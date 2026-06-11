"""
Migración de datos: siembra la configuración real del préstamo y los
movimientos de los meses 1-4. Equivale a `python manage.py seed_prestamo`,
pero corre automáticamente en cada `migrate` (y por tanto en el deploy de
Railway) UNA sola vez. Idempotente: si ya existe una configuración activa,
no hace nada (no pisa datos cargados a mano).

Los snapshots `PeriodoCalculado` no se generan aquí: el primer request a
`/api/prestamo/proyeccion/` los recalcula a partir de la config + abonos.
"""

from datetime import date
from decimal import Decimal

from django.db import migrations

# Corte del mes 1 (igual que el comando seed_prestamo).
FECHA_PRIMER_CORTE = date(2026, 2, 11)

# Movimientos bitácora meses 1-4 (ya ejecutados, SIN abonos).
# (fecha_corte, [(tipo, tramo, monto), ...])
MOVIMIENTOS_1_A_4 = [
    (date(2026, 2, 11), [
        ("cuota_amigo", "amigo", "1329824.71"),
        ("comision_2pct", "amigo", "900000.00"),
    ]),
    (date(2026, 3, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "787156.64"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
    (date(2026, 4, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "775586.84"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
    (date(2026, 5, 11), [
        ("cuota_amigo", "amigo", "1179927.31"),
        ("comision_2pct", "amigo", "763840.24"),
        ("cuota_dueno", "dueno", "149897.40"),
    ]),
]


def seed(apps, schema_editor):
    Configuracion = apps.get_model("prestamo", "Configuracion")
    Movimiento = apps.get_model("prestamo", "Movimiento")
    Tramo = apps.get_model("prestamo", "Tramo")

    # Guard: si ya hay configuración activa, no sembrar (evita pisar datos).
    if Configuracion.objects.filter(activa=True).exists():
        return

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
                fecha=fecha, nota="Seed inicial",
            )


def unseed(apps, schema_editor):
    # No-op: no borramos datos financieros automáticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("prestamo", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
