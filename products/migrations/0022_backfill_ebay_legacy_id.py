import re

from django.db import migrations

# eBay item URL pattern. Inlined on purpose: data migrations must not import
# app code (products.services.ebay_service) so they keep working even if that
# module changes or is removed later.
EBAY_ITM_RE = re.compile(r'/itm/(?:[^/]+/)?(\d+)')


def backfill_ebay_legacy_id(apps, schema_editor):
    """Populate BajoPedido.ebay_legacy_id from enlace_proveedor when possible."""
    BajoPedido = apps.get_model('products', 'BajoPedido')

    to_update = []
    queryset = BajoPedido.objects.filter(
        ebay_legacy_id__isnull=True,
    ).exclude(
        enlace_proveedor__isnull=True,
    ).exclude(
        enlace_proveedor='',
    ).only('id', 'enlace_proveedor', 'ebay_legacy_id')

    for bp in queryset.iterator():
        try:
            match = EBAY_ITM_RE.search(bp.enlace_proveedor or '')
            if match:
                bp.ebay_legacy_id = match.group(1)
                to_update.append(bp)
        except Exception:
            # Defensive: a malformed row must not break the whole migration.
            continue

    if to_update:
        BajoPedido.objects.bulk_update(to_update, ['ebay_legacy_id'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0021_bajopedido_disponibilidad_ebay_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_ebay_legacy_id, migrations.RunPython.noop),
    ]
