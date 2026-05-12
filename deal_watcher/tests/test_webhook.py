"""
Tests for the Telegram webhook view.

We patch the outbound Telegram helpers (`send_plain_message`,
`answer_callback_query`) so the test suite never hits the network. The
webhook itself is exercised through APIClient.
"""
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from deal_watcher.models import (
    NotificationPause,
    TelegramSubscriber,
)
from deal_watcher.services import pause_service
from deal_watcher.tests.factories import (
    NotificationPauseFactory,
    TelegramSubscriberFactory,
)


pytestmark = pytest.mark.django_db


WEBHOOK_SECRET = 's3cr3t'


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def url():
    return reverse('deal-watcher-telegram-webhook', kwargs={'secret': WEBHOOK_SECRET})


@pytest.fixture(autouse=True)
def _configure_secret(settings):
    settings.TELEGRAM_WEBHOOK_SECRET = WEBHOOK_SECRET
    settings.TELEGRAM_BOT_TOKEN = 'fake-token'


@pytest.fixture(autouse=True)
def _silence_outbound():
    with patch('deal_watcher.views.tg.send_plain_message') as send_mock, \
         patch('deal_watcher.views.tg.answer_callback_query') as ack_mock:
        send_mock.return_value = True
        ack_mock.return_value = True
        yield {'send': send_mock, 'ack': ack_mock}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_bad_secret_returns_403(client, settings):
    bad_url = '/deal-watcher/telegram/webhook/wrong-secret/'
    response = client.post(bad_url, data={}, format='json')
    assert response.status_code == 403


def test_missing_configured_secret_returns_503(client, url, settings):
    settings.TELEGRAM_WEBHOOK_SECRET = ''
    response = client.post(url, data={}, format='json')
    assert response.status_code == 503


def test_empty_update_still_returns_200(client, url):
    response = client.post(url, data={}, format='json')
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

def test_start_creates_subscriber(client, url, _silence_outbound):
    payload = {
        'message': {
            'chat': {'id': 123456},
            'from': {'id': 99, 'username': 'santi'},
            'text': '/start',
        }
    }
    response = client.post(url, data=payload, format='json')
    assert response.status_code == 200
    sub = TelegramSubscriber.objects.get(chat_id='123456')
    assert sub.active is True
    assert sub.telegram_username == 'santi'
    _silence_outbound['send'].assert_called_once()


def test_start_reactivates_existing_inactive_subscriber(client, url):
    TelegramSubscriberFactory(chat_id='123456', active=False, telegram_username='old')
    payload = {
        'message': {
            'chat': {'id': 123456},
            'from': {'username': 'newname'},
            'text': '/start',
        }
    }
    client.post(url, data=payload, format='json')
    sub = TelegramSubscriber.objects.get(chat_id='123456')
    assert sub.active is True
    assert sub.telegram_username == 'newname'


def test_start_with_bot_mention_is_handled(client, url):
    """Telegram clients send '/start@BotName' in groups; we strip the mention."""
    payload = {
        'message': {
            'chat': {'id': 123456},
            'from': {'username': 'santi'},
            'text': '/start@DealWatcherBot',
        }
    }
    response = client.post(url, data=payload, format='json')
    assert response.status_code == 200
    assert TelegramSubscriber.objects.filter(chat_id='123456', active=True).exists()


# ---------------------------------------------------------------------------
# /stop
# ---------------------------------------------------------------------------

def test_stop_deactivates_subscriber(client, url):
    TelegramSubscriberFactory(chat_id='123456', active=True)
    payload = {
        'message': {'chat': {'id': 123456}, 'text': '/stop'}
    }
    response = client.post(url, data=payload, format='json')
    assert response.status_code == 200
    assert TelegramSubscriber.objects.get(chat_id='123456').active is False


# ---------------------------------------------------------------------------
# /estado and /reanudar
# ---------------------------------------------------------------------------

def test_estado_reports_no_pause(client, url, _silence_outbound):
    payload = {'message': {'chat': {'id': 1}, 'text': '/estado'}}
    client.post(url, data=payload, format='json')
    text = _silence_outbound['send'].call_args.args[1]
    assert '🟢' in text


def test_estado_reports_active_pause(client, url, _silence_outbound):
    NotificationPauseFactory(
        scope=NotificationPause.SCOPE_GLOBAL,
        paused_until=timezone.now() + timedelta(hours=2),
    )
    payload = {'message': {'chat': {'id': 1}, 'text': '/estado'}}
    client.post(url, data=payload, format='json')
    text = _silence_outbound['send'].call_args.args[1]
    assert '🔴' in text


def test_reanudar_lifts_global_pause(client, url):
    NotificationPauseFactory(scope=NotificationPause.SCOPE_GLOBAL, paused_until=None)
    assert pause_service.is_globally_paused() is True
    payload = {'message': {'chat': {'id': 1}, 'text': '/reanudar'}}
    response = client.post(url, data=payload, format='json')
    assert response.status_code == 200
    assert pause_service.is_globally_paused() is False


# ---------------------------------------------------------------------------
# Callback queries (pause buttons)
# ---------------------------------------------------------------------------

def test_callback_30m_creates_global_pause(client, url, _silence_outbound):
    payload = {
        'callback_query': {
            'id': 'cb_1',
            'data': 'dw:gpause:30m',
            'from': {'username': 'santi'},
            'message': {'chat': {'id': 1}, 'message_id': 99},
        }
    }
    before = timezone.now()
    response = client.post(url, data=payload, format='json')
    assert response.status_code == 200

    pause = NotificationPause.objects.get()
    assert pause.scope == NotificationPause.SCOPE_GLOBAL
    assert pause.created_via == NotificationPause.CREATED_VIA_TELEGRAM
    assert pause.paused_until is not None
    expected = before + timedelta(minutes=30)
    # Allow a few seconds of slack between "before" and the actual creation time.
    assert abs((pause.paused_until - expected).total_seconds()) < 5
    _silence_outbound['ack'].assert_called_once()


def test_callback_indefinite_creates_pause_with_null_until(client, url):
    payload = {
        'callback_query': {
            'id': 'cb_2',
            'data': 'dw:gpause:inf',
            'from': {'username': 'santi'},
            'message': {'chat': {'id': 1}, 'message_id': 99},
        }
    }
    client.post(url, data=payload, format='json')
    pause = NotificationPause.objects.get()
    assert pause.paused_until is None


def test_unknown_callback_does_not_create_pause(client, url, _silence_outbound):
    payload = {
        'callback_query': {
            'id': 'cb_3',
            'data': 'dw:gpause:zzz',  # bad code
            'from': {},
            'message': {'chat': {'id': 1}},
        }
    }
    response = client.post(url, data=payload, format='json')
    assert response.status_code == 200
    assert NotificationPause.objects.count() == 0
    _silence_outbound['ack'].assert_called_once()
