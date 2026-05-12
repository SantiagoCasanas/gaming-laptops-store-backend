from datetime import timedelta

import pytest
from django.utils import timezone

from deal_watcher.models import NotificationPause
from deal_watcher.services import pause_service
from deal_watcher.tests.factories import (
    MonitoredProductFactory,
    NotificationPauseFactory,
)


pytestmark = pytest.mark.django_db


def test_no_pauses_means_not_paused():
    product = MonitoredProductFactory()
    assert pause_service.is_globally_paused() is False
    assert pause_service.is_product_paused(product) is False


def test_indefinite_global_pause_blocks_everything():
    product = MonitoredProductFactory()
    NotificationPauseFactory(scope=NotificationPause.SCOPE_GLOBAL, paused_until=None)
    assert pause_service.is_globally_paused() is True
    assert pause_service.is_product_paused(product) is True


def test_future_global_pause_is_active():
    product = MonitoredProductFactory()
    NotificationPauseFactory(
        scope=NotificationPause.SCOPE_GLOBAL,
        paused_until=timezone.now() + timedelta(hours=1),
    )
    assert pause_service.is_globally_paused() is True
    assert pause_service.is_product_paused(product) is True


def test_expired_global_pause_is_inactive():
    product = MonitoredProductFactory()
    NotificationPauseFactory(
        scope=NotificationPause.SCOPE_GLOBAL,
        paused_until=timezone.now() - timedelta(minutes=1),
    )
    assert pause_service.is_globally_paused() is False
    assert pause_service.is_product_paused(product) is False


def test_deactivated_global_pause_is_ignored():
    product = MonitoredProductFactory()
    NotificationPauseFactory(
        scope=NotificationPause.SCOPE_GLOBAL,
        paused_until=None,
        active=False,
    )
    assert pause_service.is_globally_paused() is False
    assert pause_service.is_product_paused(product) is False


def test_product_pause_only_affects_that_product():
    a = MonitoredProductFactory()
    b = MonitoredProductFactory()
    NotificationPauseFactory(
        scope=NotificationPause.SCOPE_PRODUCT,
        monitored_product=a,
        paused_until=None,
    )
    assert pause_service.is_product_paused(a) is True
    assert pause_service.is_product_paused(b) is False
    assert pause_service.is_globally_paused() is False


def test_create_global_pause_helper():
    until = timezone.now() + timedelta(hours=2)
    p = pause_service.create_global_pause(paused_until=until, reason='test')
    assert p.scope == NotificationPause.SCOPE_GLOBAL
    assert p.paused_until == until
    assert pause_service.is_globally_paused() is True


def test_create_product_pause_helper():
    product = MonitoredProductFactory()
    p = pause_service.create_product_pause(product=product, paused_until=None, reason='hold')
    assert p.scope == NotificationPause.SCOPE_PRODUCT
    assert p.monitored_product_id == product.pk
    assert pause_service.is_product_paused(product) is True


def test_deactivate_active_pauses_lifts_global_pause():
    NotificationPauseFactory(scope=NotificationPause.SCOPE_GLOBAL, paused_until=None)
    NotificationPauseFactory(scope=NotificationPause.SCOPE_GLOBAL, paused_until=None)
    updated = pause_service.deactivate_active_pauses(scope=NotificationPause.SCOPE_GLOBAL)
    assert updated == 2
    assert pause_service.is_globally_paused() is False
