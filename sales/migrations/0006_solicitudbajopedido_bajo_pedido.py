from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_remove_category_productocategoria'),
        ('sales', '0005_venta_estado_entrega_venta_fecha_entrega_and_more'),
    ]

    operations = [
        # Clear old unique_together first (before removing fields it references)
        migrations.AlterUniqueTogether(
            name='solicitudbajopedido',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='solicitudbajopedido',
            name='condicion',
        ),
        migrations.RemoveField(
            model_name='solicitudbajopedido',
            name='producto',
        ),
        migrations.AddField(
            model_name='solicitudbajopedido',
            name='bajo_pedido',
            field=models.ForeignKey(
                help_text='On-demand product listing the customer is requesting',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='solicitudes_bajo_pedido',
                to='products.bajopedido',
                null=True,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='solicitudbajopedido',
            name='bajo_pedido',
            field=models.ForeignKey(
                help_text='On-demand product listing the customer is requesting',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='solicitudes_bajo_pedido',
                to='products.bajopedido',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='solicitudbajopedido',
            unique_together={('bajo_pedido', 'cliente')},
        ),
    ]
