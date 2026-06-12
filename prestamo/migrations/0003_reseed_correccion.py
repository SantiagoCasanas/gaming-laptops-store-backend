"""
Migración correctiva: corrige el calendario del préstamo.

El primer corte real fue el 11 de MARZO de 2026 (no febrero). Por tanto:
  mes 1 = 11 mar, mes 2 = 11 abr, mes 3 = 11 may, mes 4 = 11 jun (este mes).
Hoy hay 4 meses pagados; el próximo pendiente es el mes 5 (11 jul).

A diferencia de 0002 (que tiene guard), esta migración RE-SIEMBRA: borra los
datos del préstamo (config + movimientos + snapshots) y los vuelve a crear
correctos. Corre UNA sola vez (Django la marca como aplicada y no se repite).

NOTA: es destructiva por diseño (lo pidió el usuario para corregir la carga
histórica). Como se setea desde cero, los snapshots PeriodoCalculado se
regeneran solos en el primer request a /api/prestamo/proyeccion/.
"""

from datetime import date
from decimal import Decimal

from django.db import migrations

FECHA_PRIMER_CORTE = date(2026, 3, 11)

# Movimientos bitácora meses 1-4 (ya pagados, SIN abonos).
MOVIMIENTOS_1_A_4 = [
    (date(2026, 3, 11), [
        ("cuota_amigo", "amigo", "1329824.71"),
        ("comision_2pct", "amigo", "900000.00"),
    ]),
    (date(2026, 4, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "787156.64"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
    (date(2026, 5, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "775586.84"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
    (date(2026, 6, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "763840.24"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
]


def reseed(apps, schema_editor):
    Configuracion = apps.get_model("prestamo", "Configuracion")
    Movimiento = apps.get_model("prestamo", "Movimiento")
    PeriodoCalculado = apps.get_model("prestamo", "PeriodoCalculado")
    Tramo = apps.get_model("prestamo", "Tramo")

    # Reset total de los datos del préstamo.
    Movimiento.objects.all().delete()
    PeriodoCalculado.objects.all().delete()
    Configuracion.objects.all().delete()

    Configuracion.objects.create(
        capital=Decimal("45000000"),
        ea=Decimal("0.1996"),
        i_m=Decimal("0.015281263150"),
        plazo=48,
        dia_corte=11,
        mes_renegociacion=2,
        comision_pct=Decimal("0.02"),
        saldo_dueno=Decimal("5000000"),
        saldo_amigo_reneg=Decimal("40000000"),
        fecha_primer_corte=FECHA_PRIMER_CORTE,
        activa=True,
    )

    for nombre in ("amigo", "dueno"):
        Tramo.objects.get_or_create(nombre=nombre)

    for fecha, items in MOVIMIENTOS_1_A_4:
        for tipo, tramo, monto in items:
            Movimiento.objects.create(
                tipo=tipo, tramo=tramo, monto=Decimal(monto),
                fecha=fecha, nota="Seed inicial (corrección)",
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("prestamo", "0002_seed_inicial"),
    ]

    operations = [
        migrations.RunPython(reseed, noop),
    ]
