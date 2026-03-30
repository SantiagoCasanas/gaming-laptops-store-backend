from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_campoproducto_proveedor_tipoproducto_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producto',
            name='categorias',
        ),
        migrations.DeleteModel(
            name='ProductoCategoria',
        ),
        migrations.DeleteModel(
            name='Category',
        ),
    ]
