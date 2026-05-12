"""
Integration-ish tests for the orchestrator. eBay HTTP and TRM lookup are
mocked; cache and DB are real (in-memory test DB + LocMem cache).
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.core.cache import cache
from django.utils import timezone

from deal_watcher.models import (
    MonitoredProduct,
    NotificationPause,
    PriceCheck,
)
from deal_watcher.services import deal_checker
from deal_watcher.services.deal_checker import SkipReason, check_one
from deal_watcher.tests.factories import (
    MonitoredProductFactory,
    NotificationPauseFactory,
    TrustedSellerFactory,
)


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _payload(price='560.00', seller='antonline', available=True, qty=3):
    return {
        'price': {'value': price, 'currency': 'USD'},
        'seller': {'username': seller},
        'estimatedAvailabilities': [
            {
                'estimatedAvailabilityStatus': 'IN_STOCK' if available else 'OUT_OF_STOCK',
                'estimatedAvailableQuantity': qty if available else 0,
            },
        ],
        'condition': 'Manufacturer Refurbished',
    }


def _patch_ebay(payload=None, side_effect=None):
    if side_effect is not None:
        return patch('deal_watcher.services.deal_checker.get_ebay_item_data', side_effect=side_effect)
    return patch('deal_watcher.services.deal_checker.get_ebay_item_data', return_value=payload)


def _patch_trm(value=Decimal('4000.00'), side_effect=None):
    if side_effect is not None:
        return patch('deal_watcher.services.deal_checker.get_trm_value_for_date', side_effect=side_effect)
    return patch('deal_watcher.services.deal_checker.get_trm_value_for_date', return_value=value)


# ---------------------------------------------------------------------------
# Pause skips
# ---------------------------------------------------------------------------

def test_skips_when_globally_paused():
    product = MonitoredProductFactory()
    NotificationPauseFactory(scope=NotificationPause.SCOPE_GLOBAL, paused_until=None)

    with _patch_ebay({}) as ebay_mock:
        outcome = check_one(product)

    assert outcome.skip_reason == SkipReason.PAUSED_GLOBAL
    assert outcome.notified is False
    ebay_mock.assert_not_called()
    assert PriceCheck.objects.filter(monitored_product=product).count() == 1


def test_skips_when_product_paused():
    product = MonitoredProductFactory()
    NotificationPauseFactory(
        scope=NotificationPause.SCOPE_PRODUCT,
        monitored_product=product,
        paused_until=None,
    )
    with _patch_ebay({}) as ebay_mock:
        outcome = check_one(product)

    assert outcome.skip_reason == SkipReason.PAUSED_PRODUCT
    ebay_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def test_ebay_error_records_price_check_with_error():
    product = MonitoredProductFactory()
    with _patch_ebay(side_effect=RuntimeError('boom')):
        outcome = check_one(product)

    assert outcome.skip_reason == SkipReason.EBAY_ERROR
    assert 'boom' in outcome.error_message
    pc = PriceCheck.objects.get(monitored_product=product)
    assert pc.was_available is False
    assert 'boom' in pc.error_message


def test_no_trm_records_check_but_skips_decision():
    product = MonitoredProductFactory()
    TrustedSellerFactory(username='antonline')
    with _patch_ebay(_payload()), _patch_trm(side_effect=ValueError('no trm')):
        outcome = check_one(product)

    assert outcome.skip_reason == SkipReason.NO_TRM
    pc = PriceCheck.objects.get(monitored_product=product)
    assert 'no trm' in pc.error_message


# ---------------------------------------------------------------------------
# Decision pipeline
# ---------------------------------------------------------------------------

def test_skips_when_not_available():
    product = MonitoredProductFactory(max_price_cop=Decimal('5000000'))
    TrustedSellerFactory(username='antonline')
    with _patch_ebay(_payload(available=False)), _patch_trm():
        outcome = check_one(product)

    assert outcome.skip_reason == SkipReason.NOT_AVAILABLE
    assert outcome.notified is False


def test_skips_when_seller_untrusted():
    product = MonitoredProductFactory(max_price_cop=Decimal('5000000'))
    # No TrustedSeller created
    with _patch_ebay(_payload(seller='randomguy')), _patch_trm():
        outcome = check_one(product)

    assert outcome.skip_reason == SkipReason.UNTRUSTED_SELLER
    assert outcome.notified is False


def test_skips_when_price_too_high():
    product = MonitoredProductFactory(max_price_cop=Decimal('1000000'))  # 1M COP
    TrustedSellerFactory(username='antonline')
    # 560 USD * 4000 TRM = 2.24M > 1M
    with _patch_ebay(_payload()), _patch_trm():
        outcome = check_one(product)

    assert outcome.skip_reason == SkipReason.PRICE_TOO_HIGH
    assert outcome.notified is False


def test_notifies_when_all_conditions_met():
    product = MonitoredProductFactory(max_price_cop=Decimal('2500000'))  # 2.5M COP
    TrustedSellerFactory(username='antonline')
    notifier = MagicMock()

    with _patch_ebay(_payload()), _patch_trm(value=Decimal('4000.00')):
        outcome = check_one(product, notifier=notifier)

    assert outcome.notified is True
    assert outcome.skip_reason is None
    assert outcome.price_usd == Decimal('560.00')
    assert outcome.price_cop == Decimal('2240000.00')
    assert outcome.seller_is_trusted is True
    notifier.assert_called_once()

    product.refresh_from_db()
    assert product.last_notified_price_usd == Decimal('560.00')
    assert product.last_notified_at is not None


def test_cooldown_blocks_second_notification_same_price():
    product = MonitoredProductFactory(max_price_cop=Decimal('2500000'))
    TrustedSellerFactory(username='antonline')

    with _patch_ebay(_payload()), _patch_trm(value=Decimal('4000.00')):
        first = check_one(product)
        second = check_one(product)

    assert first.notified is True
    assert second.notified is False
    assert second.skip_reason == SkipReason.COOLDOWN


def test_dry_run_does_not_set_cooldown_or_call_notifier():
    product = MonitoredProductFactory(max_price_cop=Decimal('2500000'))
    TrustedSellerFactory(username='antonline')
    notifier = MagicMock()

    with _patch_ebay(_payload()), _patch_trm(value=Decimal('4000.00')):
        outcome = check_one(product, notifier=notifier, dry_run=True)

    assert outcome.notified is True  # intent recorded
    notifier.assert_not_called()
    # No cooldown set: a real run right after still notifies
    product.refresh_from_db()
    assert product.last_notified_at is None  # not persisted in dry_run


def test_observation_persists_even_when_skipped_for_price():
    product = MonitoredProductFactory(max_price_cop=Decimal('1000000'))
    TrustedSellerFactory(username='antonline')

    with _patch_ebay(_payload()), _patch_trm():
        check_one(product)

    product.refresh_from_db()
    assert product.last_known_price_usd == Decimal('560.00')
    assert product.last_known_seller == 'antonline'
    assert product.last_seen_available_at is not None


# ---------------------------------------------------------------------------
# Run summary
# ---------------------------------------------------------------------------

def test_check_all_active_processes_each_product_and_summarises():
    p1 = MonitoredProductFactory(max_price_cop=Decimal('5000000'))
    p2 = MonitoredProductFactory(max_price_cop=Decimal('100000'))  # too cheap → skip
    MonitoredProductFactory(active=False)  # inactive → ignored
    TrustedSellerFactory(username='antonline')

    with _patch_ebay(_payload()), _patch_trm(value=Decimal('4000.00')):
        summary = deal_checker.check_all_active()

    assert summary.total == 2
    assert summary.notified == 1
    assert summary.skipped == 1
    outcomes_by_id = {o.product_id: o for o in summary.outcomes}
    assert outcomes_by_id[p1.pk].notified is True
    assert outcomes_by_id[p2.pk].skip_reason == SkipReason.PRICE_TOO_HIGH
