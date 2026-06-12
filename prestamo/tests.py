"""
Tests de integración de la API `prestamo` (Milestone 1 DoD).

Ejecutar:  python manage.py test prestamo
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from prestamo.engine import tasa_mensual
from prestamo.models import (
    AuditLog, Configuracion, Movimiento, PeriodoCalculado, Tramo,
)
from prestamo import services

User = get_user_model()


def _seed_config():
    ea = Decimal("0.1996")
    return Configuracion.objects.create(
        capital=Decimal("45000000"), ea=ea, i_m=tasa_mensual(ea),
        plazo=48, dia_corte=11, mes_renegociacion=2,
        comision_pct=Decimal("0.02"), saldo_dueno=Decimal("5000000"),
        saldo_amigo_reneg=Decimal("40000000"),
        fecha_primer_corte=date(2026, 2, 11), activa=True,
    )


class PrestamoAPITests(APITestCase):
    def setUp(self):
        # Las migraciones de datos (0002/0003) siembran una base; la limpiamos
        # para que cada test parta de cero y sea determinista.
        Movimiento.objects.all().delete()
        PeriodoCalculado.objects.all().delete()
        Configuracion.objects.all().delete()
        Tramo.objects.all().delete()

        self.user = User.objects.create_user(email="a@b.com", password="x")
        self.client.force_authenticate(self.user)
        self.config = _seed_config()
        Tramo.objects.get_or_create(nombre=Tramo.AMIGO)
        Tramo.objects.get_or_create(nombre=Tramo.DUENO)
        services.recalcular(self.config)

    def test_requiere_autenticacion(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/prestamo/resumen/")
        self.assertIn(resp.status_code, (401, 403))

    def test_resumen(self):
        resp = self.client.get("/api/prestamo/resumen/")
        self.assertEqual(resp.status_code, 200)
        r = resp.data["resumen"]
        self.assertTrue(r["configurado"])
        self.assertIn("amigo", r)
        self.assertIn("proxima_cuota", r["amigo"])

    def test_proyeccion_48_meses_reproduce_tabla(self):
        resp = self.client.get("/api/prestamo/proyeccion/")
        self.assertEqual(resp.status_code, 200)
        proy = resp.data["proyeccion"]
        self.assertEqual(len(proy), 48)
        # Saldo fin banco mes 1-4 contra la tabla §2 (tolerancia <= 1 peso).
        esperado = {1: "44357832.13", 2: "43705851.13",
                    3: "43043907.04", 4: "42371847.60"}
        for mes, val in esperado.items():
            actual = Decimal(proy[mes - 1]["banco"]["saldo_final"])
            self.assertLessEqual(abs(actual - Decimal(val)), Decimal("1"))

    def test_crear_movimiento_dispara_recalculo_y_auditoria(self):
        # Abono del amigo en el mes 5 (junio): baja su saldo.
        saldo_antes = Decimal(self.client.get("/api/prestamo/proyeccion/").data
                              ["proyeccion"][4]["amigo"]["saldo_final"])
        payload = {
            "tipo": "abono_amigo", "monto": "5000000",
            "fecha": "2026-06-05", "nota": "Abono test",
        }
        resp = self.client.post("/api/prestamo/movimientos/", payload)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["movimiento"]["tramo"], "amigo")  # derivado

        saldo_despues = Decimal(self.client.get("/api/prestamo/proyeccion/").data
                                ["proyeccion"][4]["amigo"]["saldo_final"])
        self.assertLess(saldo_despues, saldo_antes)

        # Auditoría registrada.
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.CREAR).exists())

    def test_monto_invalido_rechazado(self):
        resp = self.client.post("/api/prestamo/movimientos/", {
            "tipo": "abono_amigo", "monto": "0", "fecha": "2026-06-05",
        })
        self.assertEqual(resp.status_code, 400)

    def test_tipo_tramo_inconsistente_rechazado(self):
        resp = self.client.post("/api/prestamo/movimientos/", {
            "tipo": "abono_amigo", "tramo": "dueno",
            "monto": "1000", "fecha": "2026-06-05",
        })
        self.assertEqual(resp.status_code, 400)

    def test_editar_y_borrar_movimiento(self):
        mov = Movimiento.objects.create(
            tipo="abono_amigo", tramo="amigo", monto=Decimal("1000000"),
            fecha=date(2026, 6, 5),
        )
        # PATCH
        resp = self.client.patch(f"/api/prestamo/movimientos/{mov.id}/",
                                 {"monto": "2000000"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(resp.data["movimiento"]["monto"]), Decimal("2000000.00"))
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.EDITAR).exists())
        # DELETE
        resp = self.client.delete(f"/api/prestamo/movimientos/{mov.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Movimiento.objects.filter(id=mov.id).exists())
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.BORRAR).exists())

    def test_auditoria_endpoint(self):
        self.client.post("/api/prestamo/movimientos/", {
            "tipo": "abono_amigo", "monto": "1000000", "fecha": "2026-06-05",
        })
        resp = self.client.get("/api/prestamo/auditoria/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["auditoria"]), 1)

    def test_pago_regular_preview(self):
        resp = self.client.get("/api/prestamo/pago-regular/", {"mes": 5})
        self.assertEqual(resp.status_code, 200)
        pr = resp.data["pago_regular"]
        self.assertEqual(pr["mes"], 5)
        self.assertFalse(pr["ya_pagado"])
        # Mes 5 (sin abonos): cuota amigo, cuota dueño y 2% > 0.
        self.assertGreater(Decimal(pr["cuota_amigo"]), 0)
        self.assertGreater(Decimal(pr["cuota_dueno"]), 0)
        self.assertGreater(Decimal(pr["comision_2pct"]), 0)
        self.assertEqual(
            Decimal(pr["total"]),
            Decimal(pr["cuota_amigo"]) + Decimal(pr["cuota_dueno"]) + Decimal(pr["comision_2pct"]),
        )

    def test_pago_regular_registra_tres_movimientos_e_idempotente(self):
        antes = Movimiento.objects.count()
        resp = self.client.post("/api/prestamo/pago-regular/", {"mes": 5})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp.data["movimientos"]), 3)
        tipos = {m["tipo"] for m in resp.data["movimientos"]}
        self.assertEqual(tipos, {"cuota_amigo", "cuota_dueno", "comision_2pct"})
        self.assertEqual(Movimiento.objects.count(), antes + 3)
        # Auditoría: 3 entradas de creación.
        self.assertEqual(AuditLog.objects.filter(accion=AuditLog.CREAR).count(), 3)
        # Segundo intento del mismo período: rechazado.
        resp2 = self.client.post("/api/prestamo/pago-regular/", {"mes": 5})
        self.assertEqual(resp2.status_code, 400)

    def test_pago_regular_con_comprobante(self):
        url = "https://r2.example.com/prestamo/comprobantes/abc.pdf"
        resp = self.client.post(
            "/api/prestamo/pago-regular/", {"mes": 6, "comprobante_url": url}
        )
        self.assertEqual(resp.status_code, 201)
        # El comprobante se adjunta a las 3 líneas.
        for m in resp.data["movimientos"]:
            self.assertEqual(m["comprobante_url"], url)

    def test_comprobante_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        archivo = SimpleUploadedFile("recibo.png", b"fakeimagebytes",
                                     content_type="image/png")
        resp = self.client.post("/api/prestamo/comprobantes/",
                                {"archivo": archivo}, format="multipart")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("comprobante_url", resp.data)
        self.assertTrue(resp.data["comprobante_url"])
