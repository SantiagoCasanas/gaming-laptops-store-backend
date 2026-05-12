"""Tests for the notifier orchestrator (channel fan-out and error isolation)."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from deal_watcher.services.deal_checker import CheckOutcome
from deal_watcher.services.ebay_helpers import EbayItemSnapshot
from deal_watcher.services import notifier as notifier_module
from deal_watcher.tests.factories import MonitoredProductFactory


pytestmark = pytest.mark.django_db


def _snapshot():
    return EbayItemSnapshot(
        price_usd=Decimal('560.00'),
        seller_username='antonline',
        is_available=True,
        available_quantity=3,
        condition='Refurbished',
    )


def _outcome():
    return CheckOutcome(product_id=1, notified=True, price_usd=Decimal('560'))


def test_notify_calls_telegram_channel():
    product = MonitoredProductFactory()
    snapshot = _snapshot()
    outcome = _outcome()
    telegram_fake = MagicMock(return_value=4)

    result = notifier_module.notify(
        product, snapshot, outcome,
        channels={'telegram': telegram_fake},
    )

    telegram_fake.assert_called_once_with(product, snapshot, outcome)
    assert result.telegram_chats_reached == 4


def test_notify_isolates_telegram_errors():
    product = MonitoredProductFactory()
    telegram_fake = MagicMock(side_effect=RuntimeError('telegram down'))

    result = notifier_module.notify(
        product, _snapshot(), _outcome(),
        channels={'telegram': telegram_fake},
    )

    assert result.telegram_chats_reached == 0


def test_notify_with_no_channels_returns_empty_result():
    product = MonitoredProductFactory()
    result = notifier_module.notify(product, _snapshot(), _outcome(), channels={})
    assert result.telegram_chats_reached == 0


def test_default_channels_contains_telegram_only():
    channels = notifier_module.default_channels()
    assert set(channels) == {'telegram'}
