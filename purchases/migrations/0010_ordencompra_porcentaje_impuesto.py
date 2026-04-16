from django.db import migrations


class Migration(migrations.Migration):
    """No-op migration — porcentaje_impuesto is handled as a transient field, not stored in DB."""

    dependencies = [
        ('purchases', '0009_remove_ordencompra_precio_venta'),
    ]

    operations = []
