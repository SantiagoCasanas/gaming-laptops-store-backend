"""
Telegram notifier — sends deal alerts with inline pause buttons and answers
button callbacks.

python-telegram-bot v21 is async-first. We wrap the few coroutines we need
(`bot.send_message`, `bot.answer_callback_query`) with `asyncio.run` so the
rest of the codebase stays synchronous. We do NOT spin up an Application or
Updater; webhook updates are received as plain JSON via `views.TelegramWebhookView`.

Callback data scheme (kept short — Telegram caps payload at 64 bytes):
    dw:gpause:<duration>
where duration ∈ {30m, 1h, 3h, 12h, 1d, inf}.
"""
from __future__ import annotations

import asyncio
import html
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.utils import timezone

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


CALLBACK_PREFIX = 'dw:gpause:'


# Order matches the layout the operator will see (2 rows of 3).
PAUSE_BUTTONS = [
    [
        ('30m', 'Pausar 30m', timedelta(minutes=30)),
        ('1h', 'Pausar 1h', timedelta(hours=1)),
        ('3h', 'Pausar 3h', timedelta(hours=3)),
    ],
    [
        ('12h', 'Pausar 12h', timedelta(hours=12)),
        ('1d', 'Pausar 1 día', timedelta(days=1)),
        ('inf', 'Indefinido', None),
    ],
]


# Lookup table used by the webhook to translate callback_data → timedelta.
# `None` = indefinite pause (paused_until is null).
DURATION_BY_CODE: dict[str, Optional[timedelta]] = {
    code: delta for row in PAUSE_BUTTONS for code, _, delta in row
}


# ---------------------------------------------------------------------------
# Public sync API
# ---------------------------------------------------------------------------

def send_deal_alert_telegram(product, snapshot, outcome) -> int:
    """
    Send the deal alert to every active TelegramSubscriber.

    Returns the number of chats reached (0 means token missing or no subs).
    Per-chat errors are logged and do not break the loop.
    """
    from deal_watcher.models import TelegramSubscriber  # local import: avoid app loading order issues

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured — skipping Telegram alert")
        return 0

    subscribers = list(TelegramSubscriber.objects.filter(active=True))
    if not subscribers:
        logger.info("No active Telegram subscribers — skipping Telegram alert")
        return 0

    text = build_message_text(product, snapshot, outcome)
    keyboard = build_pause_keyboard()
    bot = Bot(token=token)

    sent = 0
    for sub in subscribers:
        try:
            asyncio.run(_send_message(bot, sub.chat_id, text, keyboard))
            sent += 1
        except TelegramError as exc:
            logger.warning("Telegram send failed for chat %s: %s", sub.chat_id, exc)
        except Exception as exc:
            logger.exception("Unexpected error sending Telegram to chat %s: %s", sub.chat_id, exc)
    return sent


def send_plain_message(chat_id: str, text: str, parse_mode: Optional[str] = 'HTML') -> bool:
    """Send a plain message to a single chat. Used by the webhook for replies."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured — cannot reply")
        return False
    bot = Bot(token=token)
    try:
        asyncio.run(_send_message(bot, chat_id, text, reply_markup=None, parse_mode=parse_mode))
        return True
    except Exception as exc:
        logger.warning("Telegram reply failed for chat %s: %s", chat_id, exc)
        return False


def answer_callback_query(callback_query_id: str, text: str = '', show_alert: bool = False) -> bool:
    """ACK an inline-button press so the spinner on the user's side stops."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        return False
    bot = Bot(token=token)
    try:
        asyncio.run(bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert,
        ))
        return True
    except Exception as exc:
        logger.warning("answer_callback_query failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Builders (pure — easy to unit-test)
# ---------------------------------------------------------------------------

def build_pause_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for row in PAUSE_BUTTONS:
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"{CALLBACK_PREFIX}{code}")
            for code, label, _ in row
        ])
    return InlineKeyboardMarkup(rows)


def build_message_text(product, snapshot, outcome) -> str:
    """Compose the HTML body of the alert."""
    margin = None
    if outcome.price_cop is not None and product.max_price_cop is not None:
        margin = product.max_price_cop - outcome.price_cop

    qty = (
        f"{snapshot.available_quantity} unidades"
        if snapshot.available_quantity
        else 'cantidad no informada'
    )

    nickname = html.escape(product.nickname)
    seller = html.escape(snapshot.seller_username or '—')
    condition = html.escape(snapshot.condition or '—')
    url = product.ebay_url

    return (
        f"✅ <b>{nickname}</b> disponible a buen precio\n\n"
        f"💰 USD: {_fmt_usd(outcome.price_usd)} → COP: {_fmt_cop(outcome.price_cop)}\n"
        f"🎯 Tu máximo: COP {_fmt_cop(product.max_price_cop)} (margen: COP {_fmt_cop(margin)})\n"
        f"🏪 Seller: {seller}\n"
        f"📦 Condición: {condition}\n"
        f"📊 Disponibles: {qty}\n\n"
        f"🔗 {url}"
    )


def is_pause_callback(callback_data: Optional[str]) -> bool:
    return bool(callback_data) and callback_data.startswith(CALLBACK_PREFIX)


def parse_pause_callback(callback_data: str) -> Optional[timedelta]:
    """
    Translate `callback_data` to a `timedelta`, or `None` for indefinite.

    The caller MUST confirm `is_pause_callback(callback_data)` first; this
    function raises `ValueError` if the prefix is missing or the duration
    code is unknown.
    """
    if not is_pause_callback(callback_data):
        raise ValueError(f"Not a pause callback: {callback_data!r}")
    code = callback_data[len(CALLBACK_PREFIX):]
    if code not in DURATION_BY_CODE:
        raise ValueError(f"Unknown pause code: {code!r}")
    return DURATION_BY_CODE[code]


# ---------------------------------------------------------------------------
# Internal async helpers
# ---------------------------------------------------------------------------

async def _send_message(
    bot: Bot,
    chat_id: str,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = 'HTML',
) -> None:
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_web_page_preview=False,
    )


# ---------------------------------------------------------------------------
# Formatting helpers (mirror email_resend conventions)
# ---------------------------------------------------------------------------

def _fmt_cop(value) -> str:
    if value is None:
        return '—'
    try:
        return f"${int(value):,}".replace(',', '.')
    except (TypeError, ValueError):
        return str(value)


def _fmt_usd(value) -> str:
    if value is None:
        return '—'
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)
