"""
Migración de datos: registra el abono a capital del amigo de $700.000,
realizado en el período 5 (fecha 2026-06-12, antes del corte del 11 de julio).

Idempotente: si el abono ya existe, no hace nada. Corre una sola vez en el
deploy. Limpia los snapshots PeriodoCalculado para que la proyección se
regenere ya con el abono en el primer request.

NOTA: a partir de aquí, los pagos y abonos se registran desde la app
(botón "Registrar abono"); esta migración solo trae a prod el estado real
acumulado durante la puesta en marcha.
"""

from datetime import date
from decimal import Decimal

from django.db import migrations

FECHA = date(2026, 6, 12)
MONTO = Decimal("700000")


def crear_abono(apps, schema_editor):
    Movimiento = apps.get_model("prestamo", "Movimiento")
    PeriodoCalculado = apps.get_model("prestamo", "PeriodoCalculado")

    ya_existe = Movimiento.objects.filter(
        tipo="abono_amigo", monto=MONTO, fecha=FECHA
    ).exists()
    if ya_existe:
        return

    Movimiento.objects.create(
        tipo="abono_amigo", tramo="amigo", monto=MONTO,
        fecha=FECHA, nota="Abono amigo a capital",
    )
    # Forzar regeneración de la proyección (el motor recalcula en el próximo
    # request porque ya no hay snapshots).
    PeriodoCalculado.objects.all().delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("prestamo", "0003_reseed_correccion"),
    ]

    operations = [
        migrations.RunPython(crear_abono, noop),
    ]
