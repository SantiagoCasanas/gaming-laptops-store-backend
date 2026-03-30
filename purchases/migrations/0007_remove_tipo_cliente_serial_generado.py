from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0006_ordencompra_estado_logistico_and_more'),
        ('sales', '0005_venta_estado_entrega_venta_fecha_entrega_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ordencompra',
            name='serial_generado',
        ),
        migrations.RemoveField(
            model_name='ordencompra',
            name='tipo',
        ),
        migrations.RemoveField(
            model_name='ordencompra',
            name='cliente',
        ),
    ]
