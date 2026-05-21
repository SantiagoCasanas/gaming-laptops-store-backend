"""Tests for the Telegram notifier (sends + builders + callback parsing)."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from deal_watcher.services.deal_checker import CheckOutcome
from deal_watcher.services.ebay_helpers import EbayItemSnapshot
from deal_watcher.services.notifiers import telegram as tg
from deal_watcher.tests.factories import (
    MonitoredProductFactory,
    TelegramSubscriberFactory,
)


pytestmark = pytest.mark.django_db


def _snapshot():
    return EbayItemSnapshot(
        price_usd=Decimal('560.00'),
        seller_username='antonline',
        is_available=True,
        available_quantity=3,
        condition='Manufacturer Refurbished',
    )


def _outcome():
    return CheckOutcome(
        product_id=1,
        notified=True,
        price_usd=Decimal('560.00'),
        price_cop=Decimal('2240000.00'),
        trm_used=Decimal('4000.00'),
        seller_username='antonline',
        seller_is_trusted=True,
        was_available=True,
    )


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def test_is_pause_callback():
    assert tg.is_pause_callback('dw:gpause:30m')
    assert tg.is_pause_callback('dw:gpause:inf')
    assert not tg.is_pause_callback('foo')
    assert not tg.is_pause_callback('')
    assert not tg.is_pause_callback(None)


def test_parse_pause_callback_codes():
    assert tg.parse_pause_callback('dw:gpause:30m') == timedelta(minutes=30)
    assert tg.parse_pause_callback('dw:gpause:1h') == timedelta(hours=1)
    assert tg.parse_pause_callback('dw:gpause:1d') == timedelta(days=1)
    assert tg.parse_pause_callback('dw:gpause:inf') is None


def test_parse_pause_callback_rejects_unknown():
    with pytest.raises(ValueError):
        tg.parse_pause_callback('dw:gpause:99x')
    with pytest.raises(ValueError):
        tg.parse_pause_callback('not_a_callback')


def test_build_message_text_contains_key_fields():
    product = MonitoredProductFactory(nickname='Acer Nitro V', max_price_cop=Decimal('2500000'))
    text = tg.build_message_text(product, _snapshot(), _outcome())
    assert 'Acer Nitro V' in text
    assert 'antonline' in text
    assert '$560' in text
    assert '$2.240.000' in text
    assert '🎯' in text
    assert product.ebay_url in text


def test_build_message_text_escapes_html_in_nickname():
    product = MonitoredProductFactory(nickname='<script>x</script>')
    text = tg.build_message_text(product, _snapshot(), _outcome())
    assert '<script>' not in text
    assert '&lt;script&gt;' in text


def test_build_pause_keyboard_has_six_buttons():
    kb = tg.build_pause_keyboard()
    rows = kb.inline_keyboard
    assert len(rows) == 2
    assert all(len(r) == 3 for r in rows)
    codes = {btn.callback_data for r in rows for btn in r}
    assert codes == {f"dw:gpause:{c}" for c in ['30m', '1h', '3h', '12h', '1d', 'inf']}


def test_build_product_pause_keyboard_embeds_product_id():
    kb = tg.build_product_pause_keyboard(42)
    rows = kb.inline_keyboard
    assert len(rows) == 2
    assert all(len(r) == 3 for r in rows)
    codes = {btn.callback_data for r in rows for btn in r}
    assert codes == {f"dw:ppause:42:{c}" for c in ['30m', '1h', '3h', '12h', '1d', 'inf']}


def test_build_product_resume_keyboard():
    kb = tg.build_product_resume_keyboard(42)
    rows = kb.inline_keyboard
    assert len(rows) == 1 and len(rows[0]) == 1
    assert rows[0][0].callback_data == 'dw:presume:42'


def test_is_product_pause_callback():
    assert tg.is_product_pause_callback('dw:ppause:42:30m')
    assert not tg.is_product_pause_callback('dw:gpause:30m')
    assert not tg.is_product_pause_callback('dw:presume:42')
    assert not tg.is_product_pause_callback(None)


def test_parse_product_pause_callback_codes():
    assert tg.parse_product_pause_callback('dw:ppause:42:30m') == (42, timedelta(minutes=30))
    assert tg.parse_product_pause_callback('dw:ppause:7:1h') == (7, timedelta(hours=1))
    assert tg.parse_product_pause_callback('dw:ppause:99:inf') == (99, None)


def test_parse_product_pause_callback_rejects_bad_input():
    with pytest.raises(ValueError):
        tg.parse_product_pause_callback('dw:ppause:42:zzz')   # bad code
    with pytest.raises(ValueError):
        tg.parse_product_pause_callback('dw:ppause:abc:1h')   # non-int id
    with pytest.raises(ValueError):
        tg.parse_product_pause_callback('dw:ppause:42')       # missing code
    with pytest.raises(ValueError):
        tg.parse_product_pause_callback('dw:gpause:30m')      # wrong prefix


def test_parse_product_resume_callback():
    assert tg.parse_product_resume_callback('dw:presume:42') == 42
    with pytest.raises(ValueError):
        tg.parse_product_resume_callback('dw:presume:abc')
    with pytest.raises(ValueError):
        tg.parse_product_resume_callback('dw:gpause:30m')


# ---------------------------------------------------------------------------
# Send paths (Bot mocked)
# ---------------------------------------------------------------------------

def test_send_returns_zero_when_token_missing(settings):
    settings.TELEGRAM_BOT_TOKEN = ''
    TelegramSubscriberFactory()
    product = MonitoredProductFactory()
    sent = tg.send_deal_alert_telegram(product, _snapshot(), _outcome())
    assert sent == 0


def test_send_returns_zero_when_no_subscribers(settings):
    settings.TELEGRAM_BOT_TOKEN = 'fake-token'
    product = MonitoredProductFactory()
    sent = tg.send_deal_alert_telegram(product, _snapshot(), _outcome())
    assert sent == 0


def test_send_dispatches_to_each_active_subscriber(settings):
    settings.TELEGRAM_BOT_TOKEN = 'fake-token'
    s1 = TelegramSubscriberFactory()
    s2 = TelegramSubscriberFactory()
    TelegramSubscriberFactory(active=False)  # ignored
    product = MonitoredProductFactory()

    with patch('deal_watcher.services.notifiers.telegram._send_message') as send_mock:
        # `_send_message` is async; the implementation wraps it with asyncio.run.
        async def _ok(*args, **kwargs):
            return None
        send_mock.side_effect = _ok
        sent = tg.send_deal_alert_telegram(product, _snapshot(), _outcome())

    assert sent == 2
    chat_ids = {call.args[1] for call in send_mock.call_args_list}
    assert chat_ids == {s1.chat_id, s2.chat_id}


def test_send_continues_when_one_chat_fails(settings):
    settings.TELEGRAM_BOT_TOKEN = 'fake-token'
    bad = TelegramSubscriberFactory()
    good = TelegramSubscriberFactory()
    product = MonitoredProductFactory()

    async def _fake_send(_bot, chat_id, *args, **kwargs):
        if chat_id == bad.chat_id:
            raise RuntimeError('boom')
        return None

    with patch('deal_watcher.services.notifiers.telegram._send_message', side_effect=_fake_send):
        sent = tg.send_deal_alert_telegram(product, _snapshot(), _outcome())

    assert sent == 1  # only `good` succeeded
