"""
Siembra la configuración real del préstamo y los movimientos de los meses 1-4
(cuotas + 2%), según prestamo.md §1 y §2. Idempotente (update_or_create).

Uso:
    python manage.py seed_prestamo

Tras sembrar, recalcula los snapshots y verifica que el saldo final del banco
en los meses 1-4 coincide con la tabla de validación (tolerancia <= 1 peso).
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from prestamo import services
from prestamo.engine import tasa_mensual
from prestamo.models import Configuracion, Movimiento, Tramo

# Corte del mes 1. Elegido para que hoy (jun-2026) caiga en el período 5,
# Corte del mes 1 = 11 de marzo 2026. Así hoy (junio) el mes 4 ya está pagado
# y el próximo pendiente es el mes 5 (11 de julio).
FECHA_PRIMER_CORTE = date(2026, 3, 11)

# Movimientos bitácora de los meses 1-4 (ya pagados, SIN abonos).
# (mes, fecha_corte, [(tipo, tramo, monto), ...])
MOVIMIENTOS_1_A_4 = [
    (1, date(2026, 3, 11), [
        ("cuota_amigo", "amigo", "1329824.71"),
        ("comision_2pct", "amigo", "900000.00"),
    ]),
    (2, date(2026, 4, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "787156.64"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
    (3, date(2026, 5, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "775586.84"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
    (4, date(2026, 6, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "763840.24"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
]

# Saldo final del banco esperado por mes (tabla de validación §2).
SALDO_FIN_BANCO = {
    1: Decimal("44357832.13"),
    2: Decimal("43705851.13"),
    3: Decimal("43043907.04"),
    4: Decimal("42371847.60"),
}


class Command(BaseCommand):
    help = "Siembra config + movimientos meses 1-4 del préstamo y verifica."

    def handle(self, *args, **options):
        ea = Decimal("0.1996")
        i_m = tasa_mensual(ea)

        config, _ = Configuracion.objects.update_or_create(
            activa=True,
            defaults={
                "capital": Decimal("45000000"),
                "ea": ea,
                "i_m": i_m,
                "plazo": 48,
                "dia_corte": 11,
                "mes_renegociacion": 2,
                "comision_pct": Decimal("0.02"),
                "saldo_dueno": Decimal("5000000"),
                "saldo_amigo_reneg": Decimal("40000000"),
                "fecha_primer_corte": FECHA_PRIMER_CORTE,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Config sembrada: {config}"))

        # Tramos (cache; se refresca en recalcular).
        for nombre in (Tramo.AMIGO, Tramo.DUENO):
            Tramo.objects.get_or_create(nombre=nombre)

        # Reset limpio: borramos TODOS los movimientos previos antes de
        # registrar los meses 1-4 correctos.
        Movimiento.objects.all().delete()
        creados = 0
        for mes, fecha, items in MOVIMIENTOS_1_A_4:
            for tipo, tramo, monto in items:
                Movimiento.objects.create(
                    tipo=tipo, tramo=tramo, monto=Decimal(monto),
                    fecha=fecha, nota=f"Seed mes {mes}",
                )
                creados += 1
        self.stdout.write(self.style.SUCCESS(f"Movimientos 1-4 creados: {creados}"))

        # Recalcular snapshots.
        services.recalcular(config)
        self.stdout.write(self.style.SUCCESS("Snapshots regenerados."))

        # Verificación contra la tabla de validación.
        self.stdout.write("Verificando saldo fin banco meses 1-4...")
        proyeccion = services.get_proyeccion()
        ok = True
        for mes, esperado in SALDO_FIN_BANCO.items():
            actual = Decimal(proyeccion[mes - 1]["banco"]["saldo_final"])
            diff = abs(actual - esperado)
            estado = "OK" if diff <= Decimal("1") else "FALLA"
            if diff > Decimal("1"):
                ok = False
            self.stdout.write(
                f"  mes {mes}: {actual} (esperado {esperado}, dif={diff}) -> {estado}"
            )

        if ok:
            self.stdout.write(self.style.SUCCESS("Verificación OK: motor reproduce §2."))
        else:
            self.stdout.write(self.style.ERROR("Verificación FALLIDA: revisar el motor."))
