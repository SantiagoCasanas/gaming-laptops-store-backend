from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0008_alter_ordencompra_proveedor'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ordencompra',
            name='precio_venta',
        ),
    ]
