"""
Notifier orchestrator. Currently fan-out is single-channel (Telegram); the
dict-of-channels indirection stays so tests can swap in fakes and so a future
channel can be added without touching the call sites in `deal_checker` or the
management command.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from deal_watcher.services.notifiers import telegram

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    telegram_chats_reached: int = 0


def default_channels() -> dict[str, Callable]:
    """Real channels used in production."""
    return {
        'telegram': telegram.send_deal_alert_telegram,
    }


def notify(product, snapshot, outcome, channels: dict[str, Callable] | None = None) -> NotificationResult:
    """
    Send the alert through every configured channel.

    `channels` lets tests inject fakes; pass `default_channels()` (the default)
    to use the real Telegram adapter.

    Each channel is called inside its own try/except so a single failure
    cannot silence the others.
    """
    if channels is None:
        channels = default_channels()

    result = NotificationResult()

    if 'telegram' in channels:
        try:
            sent = channels['telegram'](product, snapshot, outcome)
            result.telegram_chats_reached = int(sent or 0)
        except Exception as exc:
            logger.exception("telegram channel raised: %s", exc)
            result.telegram_chats_reached = 0

    logger.info("Notify product=%s telegram_chats=%s", product.pk, result.telegram_chats_reached)
    return result
