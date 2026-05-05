"""
Data migration: standardize OrdenCompra.costo_importacion to COP.

Background:
  • Originally orders entered the system with costo_importacion in USD (the
    same currency as costo_compra).
  • The bulk import upload (paquetestest workflow) writes the value in COP.
  • This migration converts every USD-stored value to COP so the field has a
    single, consistent unit going forward.

Heuristic:
  • Values < 1000 are treated as USD → multiply by the TRM closest to
    fecha_compra.
  • Values >= 1000 are treated as already-in-COP and left untouched.
  • Special case: order #24 (PO-2025-22) was corrupted by an earlier locale
    bug in the bulk parser ('127.435' COP got read as 127.44 due to the dot
    being treated as a decimal separator). We restore it to 127435 since the
    source value is known.
"""
from decimal import Decimal

from django.db import migrations


def migrar_costo_importacion(apps, schema_editor):
    OrdenCompra = apps.get_model('purchases', 'OrdenCompra')
    TRMHistory = apps.get_model('core', 'TRMHistory')

    THRESHOLD_USD = Decimal('1000')   # < THRESHOLD considered USD, >= COP

    # Special-case correction for the corrupted order before the heuristic
    # runs. 127.44 was originally 127.435 COP; the dot was misparsed.
    OrdenCompra.objects.filter(pk=24, costo_importacion=Decimal('127.44')).update(
        costo_importacion=Decimal('127435')
    )

    # Snapshot TRMs sorted by date for closest-date lookup.
    trms = list(TRMHistory.objects.order_by('fecha').values('fecha', 'valor_cop'))
    if not trms:
        # No TRM data — fall back to a safe default so the migration doesn't
        # silently fail. The user can manually correct values afterwards.
        default_trm = Decimal('3700')
        trms = []

    def trm_for_date(target):
        if not trms:
            return Decimal('3700')
        if target is None:
            # Use the latest known TRM as a fallback
            return Decimal(str(trms[-1]['valor_cop']))
        # Find the TRM with the smallest absolute date difference
        best = trms[0]
        best_diff = abs((best['fecha'] - target).days)
        for entry in trms[1:]:
            diff = abs((entry['fecha'] - target).days)
            if diff < best_diff:
                best, best_diff = entry, diff
        return Decimal(str(best['valor_cop']))

    for orden in OrdenCompra.objects.exclude(costo_importacion__isnull=True):
        valor = orden.costo_importacion
        if valor is None or valor >= THRESHOLD_USD:
            # Already in COP — leave alone
            continue
        # Convert USD → COP using the TRM closest to fecha_compra (or
        # created_at if no fecha_compra).
        target_date = orden.fecha_compra or (
            orden.created_at.date() if getattr(orden, 'created_at', None) else None
        )
        trm = trm_for_date(target_date)
        nuevo = (valor * trm).quantize(Decimal('1'))
        orden.costo_importacion = nuevo
        orden.save(update_fields=['costo_importacion'])


def revertir(apps, schema_editor):
    # Best-effort reversal: if values came from a recorded TRM we could divide,
    # but we don't track the rate per row. We leave a no-op since rolling back
    # would risk silently losing precision.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0013_costo_importacion_help_text'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrar_costo_importacion, revertir),
    ]
