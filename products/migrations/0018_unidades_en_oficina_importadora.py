"""
Data migration: any UnidadProducto whose linked OrdenCompra is at the
importer office must reflect estado_producto='en_oficina_importadora'
instead of the legacy 'por_comprar' (which kept the misleading "Por Comprar"
label). 'por_comprar' is preserved for the BajoPedido sourcing flow where it
genuinely means "needs to be purchased".
"""
from django.db import migrations


def fix(apps, schema_editor):
    UnidadProducto = apps.get_model('products', 'UnidadProducto')
    units = UnidadProducto.objects.filter(
        estado_producto='por_comprar',
        orden_compra__estado_logistico='en_oficina_importadora',
    )
    units.update(estado_producto='en_oficina_importadora')


def revertir(apps, schema_editor):
    UnidadProducto = apps.get_model('products', 'UnidadProducto')
    UnidadProducto.objects.filter(
        estado_producto='en_oficina_importadora'
    ).update(estado_producto='por_comprar')


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0017_add_en_oficina_importadora_choice'),
        ('purchases', '0016_alter_ordencompra_costo_compra_and_more'),
    ]

    operations = [
        migrations.RunPython(fix, revertir),
    ]
