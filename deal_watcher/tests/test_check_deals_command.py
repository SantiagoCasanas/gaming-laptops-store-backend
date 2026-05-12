"""Tests for the `check_deals` management command."""
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError

from deal_watcher.models import PriceCheck
from deal_watcher.tests.factories import (
    MonitoredProductFactory,
    TrustedSellerFactory,
)


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _payload(price='560.00', seller='antonline'):
    return {
        'price': {'value': price, 'currency': 'USD'},
        'seller': {'username': seller},
        'estimatedAvailabilities': [{'estimatedAvailabilityStatus': 'IN_STOCK', 'estimatedAvailableQuantity': 3}],
        'condition': 'Refurbished',
    }


def test_dry_run_does_not_call_notifier():
    MonitoredProductFactory(max_price_cop=Decimal('5000000'))
    TrustedSellerFactory(username='antonline')

    with patch('deal_watcher.services.deal_checker.get_ebay_item_data', return_value=_payload()), \
         patch('deal_watcher.services.deal_checker.get_trm_value_for_date', return_value=Decimal('4000')), \
         patch('deal_watcher.services.notifier.notify') as notify_mock:
        out = StringIO()
        call_command('check_deals', '--dry-run', stdout=out)

    notify_mock.assert_not_called()
    assert 'dry_run=True' in out.getvalue()


def test_real_run_invokes_notifier():
    MonitoredProductFactory(max_price_cop=Decimal('5000000'))
    TrustedSellerFactory(username='antonline')

    with patch('deal_watcher.services.deal_checker.get_ebay_item_data', return_value=_payload()), \
         patch('deal_watcher.services.deal_checker.get_trm_value_for_date', return_value=Decimal('4000')), \
         patch('deal_watcher.services.notifier.notify') as notify_mock:
        notify_mock.return_value = type('R', (), {'telegram_chats_reached': 1})()
        out = StringIO()
        call_command('check_deals', stdout=out)

    notify_mock.assert_called_once()
    assert 'notified=1' in out.getvalue()


def test_product_flag_runs_only_for_one():
    target = MonitoredProductFactory(max_price_cop=Decimal('5000000'))
    other = MonitoredProductFactory(max_price_cop=Decimal('5000000'))
    TrustedSellerFactory(username='antonline')

    with patch('deal_watcher.services.deal_checker.get_ebay_item_data', return_value=_payload()), \
         patch('deal_watcher.services.deal_checker.get_trm_value_for_date', return_value=Decimal('4000')), \
         patch('deal_watcher.services.notifier.notify'):
        out = StringIO()
        call_command('check_deals', '--product', str(target.pk), '--dry-run', stdout=out)

    # Only the target should have a PriceCheck row.
    assert PriceCheck.objects.filter(monitored_product=target).count() == 1
    assert PriceCheck.objects.filter(monitored_product=other).count() == 0


def test_product_flag_unknown_id_raises():
    with pytest.raises(CommandError):
        call_command('check_deals', '--product', '99999', '--dry-run')
