"""End-to-end tests for the Deal Watcher admin API."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from deal_watcher.models import (
    MonitoredProduct,
    NotificationPause,
    TrustedSeller,
)
from deal_watcher.tests.factories import (
    MonitoredProductFactory,
    NotificationPauseFactory,
    PriceCheckFactory,
    TelegramSubscriberFactory,
    TrustedSellerFactory,
)
from users.models import User


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email='admin@x.com', password='pw')


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_client():
    return APIClient()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_anonymous_cannot_list_monitored_products(anon_client):
    response = anon_client.get(reverse('dw-monitored-list'))
    assert response.status_code == 401


def test_anonymous_cannot_list_sellers(anon_client):
    response = anon_client.get(reverse('dw-seller-list'))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# TrustedSeller CRUD
# ---------------------------------------------------------------------------

def test_seller_create_lowercases_username(auth_client):
    response = auth_client.post(reverse('dw-seller-create'), {'username': 'ANTOnline'}, format='json')
    assert response.status_code == 201
    assert response.data['trusted_seller']['username'] == 'antonline'


def test_seller_list_returns_active_and_inactive(auth_client):
    TrustedSellerFactory(username='antonline')
    TrustedSellerFactory(username='vipoutlet', active=False)
    response = auth_client.get(reverse('dw-seller-list'))
    assert response.status_code == 200
    usernames = {s['username'] for s in response.data}
    assert usernames == {'antonline', 'vipoutlet'}


def test_seller_update(auth_client):
    s = TrustedSellerFactory(username='antonline', display_name='')
    response = auth_client.put(
        reverse('dw-seller-update', kwargs={'pk': s.pk}),
        {'username': 'antonline', 'display_name': 'Antonline LLC', 'notes': ''},
        format='json',
    )
    assert response.status_code == 200
    s.refresh_from_db()
    assert s.display_name == 'Antonline LLC'


def test_seller_deactivate_then_activate(auth_client):
    s = TrustedSellerFactory()
    r1 = auth_client.post(reverse('dw-seller-deactivate', kwargs={'pk': s.pk}))
    assert r1.status_code == 200
    s.refresh_from_db()
    assert s.active is False

    r2 = auth_client.post(reverse('dw-seller-activate', kwargs={'pk': s.pk}))
    assert r2.status_code == 200
    s.refresh_from_db()
    assert s.active is True

    # Idempotent: re-activate fails with 400.
    r3 = auth_client.post(reverse('dw-seller-activate', kwargs={'pk': s.pk}))
    assert r3.status_code == 400


# ---------------------------------------------------------------------------
# MonitoredProduct CRUD + history
# ---------------------------------------------------------------------------

def test_monitored_create_extracts_item_id(auth_client):
    response = auth_client.post(
        reverse('dw-monitored-create'),
        {
            'nickname': 'Acer Nitro V',
            'ebay_url': 'https://www.ebay.com/itm/127565054305',
            'max_price_cop': '2500000',
        },
        format='json',
    )
    assert response.status_code == 201
    assert response.data['monitored_product']['ebay_item_id'] == '127565054305'


def test_monitored_create_rejects_unparseable_url(auth_client):
    response = auth_client.post(
        reverse('dw-monitored-create'),
        {
            'nickname': 'Bad URL',
            'ebay_url': 'https://www.ebay.com/garbage',
            'max_price_cop': '1000000',
        },
        format='json',
    )
    assert response.status_code == 400
    assert 'ebay_url' in response.data


def test_monitored_update_changes_url_and_reextracts_id(auth_client):
    p = MonitoredProductFactory()
    new_url = 'https://www.ebay.com/itm/999888777'
    response = auth_client.put(
        reverse('dw-monitored-update', kwargs={'pk': p.pk}),
        {'nickname': p.nickname, 'ebay_url': new_url, 'max_price_cop': '3000000'},
        format='json',
    )
    assert response.status_code == 200
    p.refresh_from_db()
    assert p.ebay_url == new_url
    assert p.ebay_item_id == '999888777'


def test_monitored_detail_shows_last_known_fields(auth_client):
    p = MonitoredProductFactory(last_known_price_usd=Decimal('560.00'), last_known_seller='antonline')
    response = auth_client.get(reverse('dw-monitored-detail', kwargs={'pk': p.pk}))
    assert response.status_code == 200
    assert response.data['last_known_price_usd'] == '560.00'
    assert response.data['last_known_seller'] == 'antonline'


def test_monitored_history_returns_newest_first(auth_client):
    p = MonitoredProductFactory()
    PriceCheckFactory(monitored_product=p, price_usd=Decimal('100'))
    PriceCheckFactory(monitored_product=p, price_usd=Decimal('200'))
    response = auth_client.get(reverse('dw-monitored-history', kwargs={'pk': p.pk}))
    assert response.status_code == 200
    assert len(response.data) == 2
    # first item is the newest
    assert response.data[0]['checked_at'] >= response.data[1]['checked_at']


def test_monitored_history_only_returns_for_target_product(auth_client):
    a = MonitoredProductFactory()
    b = MonitoredProductFactory()
    PriceCheckFactory(monitored_product=a)
    PriceCheckFactory(monitored_product=b)
    PriceCheckFactory(monitored_product=b)
    response = auth_client.get(reverse('dw-monitored-history', kwargs={'pk': b.pk}))
    assert len(response.data) == 2


def test_monitored_deactivate_then_activate(auth_client):
    p = MonitoredProductFactory()
    auth_client.post(reverse('dw-monitored-deactivate', kwargs={'pk': p.pk}))
    p.refresh_from_db()
    assert p.active is False
    auth_client.post(reverse('dw-monitored-activate', kwargs={'pk': p.pk}))
    p.refresh_from_db()
    assert p.active is True


# ---------------------------------------------------------------------------
# Pauses
# ---------------------------------------------------------------------------

def test_pause_status_when_no_pause(auth_client):
    response = auth_client.get(reverse('dw-pause-status'))
    assert response.status_code == 200
    assert response.data['is_paused'] is False
    assert response.data['paused_until'] is None


def test_pause_status_when_active(auth_client):
    until = timezone.now() + timedelta(hours=2)
    NotificationPauseFactory(
        scope=NotificationPause.SCOPE_GLOBAL,
        paused_until=until,
        reason='testing',
    )
    response = auth_client.get(reverse('dw-pause-status'))
    assert response.data['is_paused'] is True
    assert response.data['reason'] == 'testing'


def test_pause_create_with_duration_minutes(auth_client):
    before = timezone.now()
    response = auth_client.post(
        reverse('dw-pause-create'),
        {'duration_minutes': 30, 'reason': 'lunch'},
        format='json',
    )
    assert response.status_code == 201
    pause = NotificationPause.objects.get()
    assert pause.scope == NotificationPause.SCOPE_GLOBAL
    assert pause.created_via == NotificationPause.CREATED_VIA_UI
    assert abs((pause.paused_until - (before + timedelta(minutes=30))).total_seconds()) < 5


def test_pause_create_indefinite_when_no_input(auth_client):
    response = auth_client.post(reverse('dw-pause-create'), {}, format='json')
    assert response.status_code == 201
    pause = NotificationPause.objects.get()
    assert pause.paused_until is None


def test_pause_create_rejects_both_inputs(auth_client):
    response = auth_client.post(
        reverse('dw-pause-create'),
        {'duration_minutes': 30, 'paused_until': '2099-01-01T00:00:00Z'},
        format='json',
    )
    assert response.status_code == 400


def test_pause_lift_deactivates_active_global_pauses(auth_client):
    NotificationPauseFactory(scope=NotificationPause.SCOPE_GLOBAL, paused_until=None)
    NotificationPauseFactory(scope=NotificationPause.SCOPE_GLOBAL, paused_until=None)
    response = auth_client.post(reverse('dw-pause-lift'))
    assert response.status_code == 200
    assert response.data['lifted'] == 2
    assert NotificationPause.objects.filter(active=True, scope=NotificationPause.SCOPE_GLOBAL).count() == 0


# ---------------------------------------------------------------------------
# Telegram subscribers
# ---------------------------------------------------------------------------

def test_subscriber_list(auth_client):
    TelegramSubscriberFactory()
    TelegramSubscriberFactory()
    response = auth_client.get(reverse('dw-tg-subs-list'))
    assert response.status_code == 200
    assert len(response.data) == 2


def test_subscriber_deactivate(auth_client):
    sub = TelegramSubscriberFactory()
    response = auth_client.post(reverse('dw-tg-subs-deactivate', kwargs={'pk': sub.pk}))
    assert response.status_code == 200
    sub.refresh_from_db()
    assert sub.active is False
