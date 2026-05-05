"""
Data migration: convert OrdenCompra.costo_compra and impuesto_importacion
from USD to COP using the TRM closest to fecha_compra.

Going forward both fields are stored in COP (the canonical currency for the
whole system). The serializer/form may still let the user enter the value in
USD for convenience but the conversion happens before persistence.

Heuristic: any value below 10_000 is assumed to be USD and converted; values
already at or above the threshold are left untouched (already COP). This is
safe because typical USD purchase costs are in the hundreds while COP costs
are in the millions.
"""
from decimal import Decimal

from django.db import migrations


THRESHOLD = Decimal('10000')


def to_cop(apps, schema_editor):
    OrdenCompra = apps.get_model('purchases', 'OrdenCompra')
    TRMHistory = apps.get_model('core', 'TRMHistory')

    trms = list(TRMHistory.objects.order_by('fecha').values('fecha', 'valor_cop'))

    def trm_for_date(target):
        if not trms:
            return Decimal('3700')
        if target is None:
            return Decimal(str(trms[-1]['valor_cop']))
        best = trms[0]
        best_diff = abs((best['fecha'] - target).days)
        for entry in trms[1:]:
            diff = abs((entry['fecha'] - target).days)
            if diff < best_diff:
                best, best_diff = entry, diff
        return Decimal(str(best['valor_cop']))

    for orden in OrdenCompra.objects.all():
        target_date = orden.fecha_compra or (
            orden.created_at.date() if getattr(orden, 'created_at', None) else None
        )
        trm = trm_for_date(target_date)

        if orden.costo_compra is not None and orden.costo_compra < THRESHOLD:
            orden.costo_compra = (orden.costo_compra * trm).quantize(Decimal('1'))
        if orden.impuesto_importacion is not None and orden.impuesto_importacion < THRESHOLD:
            orden.impuesto_importacion = (orden.impuesto_importacion * trm).quantize(Decimal('1'))
        orden.save(update_fields=['costo_compra', 'impuesto_importacion'])


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0014_migrar_costo_importacion_a_cop'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(to_cop, revertir),
    ]
