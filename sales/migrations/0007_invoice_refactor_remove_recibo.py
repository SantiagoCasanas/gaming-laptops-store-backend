import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0006_solicitudbajopedido_bajo_pedido'),
    ]

    operations = [
        # 1. Remove Recibo model
        migrations.DeleteModel(
            name='Recibo',
        ),
        # 2. Remove denormalized client fields from Invoice
        migrations.RemoveField(
            model_name='invoice',
            name='client_name',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='client_document',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='client_phone',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='client_address',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='client_email',
        ),
        # 3. Add active field (from BaseModel — no-op for DB since we add default)
        migrations.AddField(
            model_name='invoice',
            name='active',
            field=models.BooleanField(default=True),
        ),
        # 4. Add cliente FK (nullable first so migration works on empty table too)
        migrations.AddField(
            model_name='invoice',
            name='cliente',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Customer this invoice belongs to',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='invoices',
                to='sales.cliente',
            ),
        ),
        # 5. Add venta FK (optional)
        migrations.AddField(
            model_name='invoice',
            name='venta',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Associated sale (optional)',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invoices',
                to='sales.venta',
            ),
        ),
        # 6. Add separacion FK (optional)
        migrations.AddField(
            model_name='invoice',
            name='separacion',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Associated hold/separation (optional)',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invoices',
                to='sales.separacion',
            ),
        ),
    ]
