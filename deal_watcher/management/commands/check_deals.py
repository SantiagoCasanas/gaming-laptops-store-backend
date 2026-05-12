"""
Manual + idempotent run of the Deal Watcher pipeline.

Usage:
    python manage.py check_deals               # real run, sends notifications
    python manage.py check_deals --dry-run     # no notifications, no cooldown side-effect
    python manage.py check_deals --product 12  # restrict to a single MonitoredProduct id
    python manage.py check_deals --test-alert 12  # send a fake alert through every channel
                                                  # (no eBay/TRM call, no cooldown). Use to
                                                  # verify Telegram + email delivery.

Logs a one-line summary at the end (always) and per-product details at INFO.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from deal_watcher.models import MonitoredProduct
from deal_watcher.services import deal_checker, notifier as notifier_module
from deal_watcher.services.deal_checker import CheckOutcome
from deal_watcher.services.ebay_helpers import EbayItemSnapshot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run a Deal Watcher check pass over every active monitored product."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Do not send notifications and do not write the cooldown key.",
        )
        parser.add_argument(
            '--product',
            type=int,
            default=None,
            help="Run only for this MonitoredProduct id.",
        )
        parser.add_argument(
            '--test-alert',
            type=int,
            default=None,
            metavar='PRODUCT_ID',
            help="Send a synthetic alert for this product through every notifier "
                 "channel. Bypasses eBay, TRM, pauses, sellers and cooldown. "
                 "Use to verify Telegram delivery.",
        )

    def handle(self, *args, **options):
        if options['test_alert'] is not None:
            self._test_alert(options['test_alert'])
            return

        dry_run: bool = options['dry_run']
        product_id: int | None = options['product']

        notifier_callable = None if dry_run else (
            lambda product, snapshot, outcome: notifier_module.notify(product, snapshot, outcome)
        )

        if product_id is not None:
            try:
                product = MonitoredProduct.objects.get(pk=product_id)
            except MonitoredProduct.DoesNotExist:
                raise CommandError(f"MonitoredProduct {product_id} not found")
            outcome = deal_checker.check_one(product, notifier=notifier_callable, dry_run=dry_run)
            self._print_outcome(outcome)
            return

        summary = deal_checker.check_all_active(notifier=notifier_callable, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS(
            f"check_deals done: total={summary.total} notified={summary.notified} "
            f"skipped={summary.skipped} errors={summary.errors} dry_run={dry_run}"
        ))
        for o in summary.outcomes:
            self._print_outcome(o)

    def _test_alert(self, product_id: int) -> None:
        try:
            product = MonitoredProduct.objects.get(pk=product_id)
        except MonitoredProduct.DoesNotExist:
            raise CommandError(f"MonitoredProduct {product_id} not found")

        # Synthetic snapshot: a "would-be deal" 10% under the operator's max.
        max_cop = product.max_price_cop or Decimal('1000000')
        fake_cop = (max_cop * Decimal('0.9')).quantize(Decimal('0.01'))
        fake_trm = Decimal('4200.00')
        fake_usd = (fake_cop / fake_trm).quantize(Decimal('0.01'))

        snapshot = EbayItemSnapshot(
            price_usd=fake_usd,
            seller_username='test-seller',
            is_available=True,
            available_quantity=1,
            condition='[TEST] Manufacturer Refurbished',
        )
        outcome = CheckOutcome(
            product_id=product.pk,
            notified=True,
            price_usd=fake_usd,
            price_cop=fake_cop,
            trm_used=fake_trm,
            seller_username='test-seller',
            seller_is_trusted=True,
            was_available=True,
        )

        result = notifier_module.notify(product, snapshot, outcome)
        self.stdout.write(self.style.SUCCESS(
            f"test alert dispatched for product={product.pk} "
            f"telegram_chats={result.telegram_chats_reached}"
        ))

    def _print_outcome(self, outcome) -> None:
        bits = [f"product={outcome.product_id}"]
        if outcome.notified:
            bits.append("NOTIFIED")
        if outcome.skip_reason:
            bits.append(f"skip={outcome.skip_reason}")
        if outcome.price_usd is not None:
            bits.append(f"usd={outcome.price_usd}")
        if outcome.price_cop is not None:
            bits.append(f"cop={outcome.price_cop}")
        if outcome.seller_username:
            bits.append(f"seller={outcome.seller_username}")
        if outcome.error_message:
            bits.append(f"err={outcome.error_message[:80]}")
        self.stdout.write(' · '.join(bits))
