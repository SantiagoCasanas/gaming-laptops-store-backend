"""
Deal checker orchestrator.

Public entry points:
- `check_all_active(notifier=None, dry_run=False)`: process every active monitored
  product. Returns a summary dict.
- `check_one(product, notifier=None, dry_run=False)`: process a single product.
  Returns a `CheckOutcome`.

The notifier is an optional callable with signature
`notifier(product, snapshot, decision)`. Session 1 leaves it None; Session 2
plugs in the real Resend + Telegram orchestrator.

Side effects per call:
- One `PriceCheck` row is always written (success or error).
- On a successful read, `MonitoredProduct.last_known_*` and
  `last_seen_available_at` are updated.
- On a notification, `last_notified_at` and `last_notified_price_usd` are set
  and the cooldown key is written to Redis.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from deal_watcher.models import (
    MonitoredProduct,
    PriceCheck,
    TrustedSeller,
)
from deal_watcher.services import pause_service
from deal_watcher.services.ebay_helpers import EbayItemSnapshot, parse_item_payload
from deal_watcher.services.trm_cache import get_trm_value_for_date

from products.services.ebay_service import get_ebay_item_data

logger = logging.getLogger(__name__)


COOLDOWN_KEY_PREFIX = 'deal_watcher:notified:'


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class SkipReason:
    PAUSED_GLOBAL = 'paused_global'
    PAUSED_PRODUCT = 'paused_product'
    EBAY_ERROR = 'ebay_error'
    NO_PRICE = 'no_price'
    NO_TRM = 'no_trm'
    NOT_AVAILABLE = 'not_available'
    UNTRUSTED_SELLER = 'untrusted_seller'
    PRICE_TOO_HIGH = 'price_too_high'
    COOLDOWN = 'cooldown'


@dataclass
class CheckOutcome:
    product_id: int
    notified: bool = False
    skip_reason: Optional[str] = None
    error_message: str = ''
    price_usd: Optional[Decimal] = None
    price_cop: Optional[Decimal] = None
    trm_used: Optional[Decimal] = None
    seller_username: str = ''
    seller_is_trusted: bool = False
    was_available: bool = False
    price_check_id: Optional[int] = None


@dataclass
class RunSummary:
    total: int = 0
    notified: int = 0
    skipped: int = 0
    errors: int = 0
    outcomes: list[CheckOutcome] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_all_active(
    notifier: Optional[Callable] = None,
    dry_run: bool = False,
) -> RunSummary:
    """Iterate every active monitored product and run the check pipeline."""
    summary = RunSummary()
    products = MonitoredProduct.objects.filter(active=True).select_related('producto_catalogo')

    for product in products:
        try:
            outcome = check_one(product, notifier=notifier, dry_run=dry_run)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unhandled error checking MonitoredProduct %s", product.pk)
            outcome = CheckOutcome(
                product_id=product.pk,
                skip_reason=SkipReason.EBAY_ERROR,
                error_message=f"Unhandled: {exc}",
            )
            summary.errors += 1
        summary.total += 1
        summary.outcomes.append(outcome)
        if outcome.notified:
            summary.notified += 1
        elif outcome.skip_reason in (SkipReason.EBAY_ERROR, SkipReason.NO_PRICE, SkipReason.NO_TRM):
            summary.errors += 1
        else:
            summary.skipped += 1

    logger.info(
        "Deal Watcher run done: total=%s notified=%s skipped=%s errors=%s (dry_run=%s)",
        summary.total, summary.notified, summary.skipped, summary.errors, dry_run,
    )
    return summary


def check_one(
    product: MonitoredProduct,
    notifier: Optional[Callable] = None,
    dry_run: bool = False,
    now: Optional[datetime] = None,
) -> CheckOutcome:
    """Run the pipeline for a single monitored product."""
    now = now or timezone.now()
    outcome = CheckOutcome(product_id=product.pk)

    # 1. Pause checks
    if pause_service.is_globally_paused(now):
        outcome.skip_reason = SkipReason.PAUSED_GLOBAL
        _write_price_check(product, outcome, was_available=False, error_message='paused: global')
        return outcome
    if pause_service.is_product_paused(product, now):
        outcome.skip_reason = SkipReason.PAUSED_PRODUCT
        _write_price_check(product, outcome, was_available=False, error_message='paused: product')
        return outcome

    # 2. Fetch eBay payload
    try:
        payload = get_ebay_item_data(product.ebay_item_id)
    except Exception as exc:
        outcome.skip_reason = SkipReason.EBAY_ERROR
        outcome.error_message = str(exc)
        _write_price_check(product, outcome, was_available=False, error_message=str(exc)[:1000])
        return outcome

    # 3. Parse payload
    try:
        snapshot = parse_item_payload(payload)
    except Exception as exc:
        outcome.skip_reason = SkipReason.EBAY_ERROR
        outcome.error_message = f"parse: {exc}"
        _write_price_check(product, outcome, was_available=False, error_message=outcome.error_message[:1000])
        return outcome

    outcome.was_available = snapshot.is_available
    outcome.seller_username = snapshot.seller_username

    if not snapshot.has_price:
        outcome.skip_reason = SkipReason.NO_PRICE
        _persist_observation(product, snapshot, now, was_available=False)
        _write_price_check(product, outcome, was_available=False, error_message='no price in payload')
        return outcome

    outcome.price_usd = snapshot.price_usd

    # 4. TRM
    try:
        trm_value = get_trm_value_for_date(timezone.localdate())
    except ValueError as exc:
        outcome.skip_reason = SkipReason.NO_TRM
        outcome.error_message = str(exc)
        _persist_observation(product, snapshot, now, was_available=snapshot.is_available)
        _write_price_check(product, outcome, was_available=snapshot.is_available, error_message=str(exc)[:1000])
        return outcome

    outcome.trm_used = trm_value
    outcome.price_cop = (snapshot.price_usd * trm_value).quantize(Decimal('0.01'))

    # 5. Persist observation regardless of decision
    _persist_observation(product, snapshot, now, was_available=snapshot.is_available)

    # 6. Decision pipeline
    if not snapshot.is_available:
        outcome.skip_reason = SkipReason.NOT_AVAILABLE
        _write_price_check(product, outcome, was_available=False)
        return outcome

    seller_is_trusted = _is_trusted(snapshot.seller_username)
    outcome.seller_is_trusted = seller_is_trusted
    if not seller_is_trusted:
        outcome.skip_reason = SkipReason.UNTRUSTED_SELLER
        _write_price_check(product, outcome, was_available=True)
        return outcome

    if outcome.price_cop > product.max_price_cop:
        outcome.skip_reason = SkipReason.PRICE_TOO_HIGH
        _write_price_check(product, outcome, was_available=True)
        return outcome

    # 7. Anti-spam cooldown
    if _in_cooldown(product, snapshot.price_usd):
        outcome.skip_reason = SkipReason.COOLDOWN
        _write_price_check(product, outcome, was_available=True)
        return outcome

    # 8. Notify
    if dry_run:
        logger.info("dry_run: would notify product %s at $%s USD", product.pk, snapshot.price_usd)
    elif notifier is not None:
        try:
            notifier(product, snapshot, outcome)
        except Exception as exc:
            logger.exception("Notifier failed for product %s", product.pk)
            outcome.error_message = f"notifier: {exc}"

    # Mark notified even in dry_run so the test/UI sees the intent. The cooldown
    # is only set when really sent (so dry runs don't suppress the next real run).
    if not dry_run and outcome.error_message == '':
        _set_cooldown(product, snapshot.price_usd)
        _persist_notification(product, snapshot, now)
        outcome.notified = True
    elif dry_run:
        outcome.notified = True

    _write_price_check(product, outcome, was_available=True)
    return outcome


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _is_trusted(username: str) -> bool:
    if not username:
        return False
    return TrustedSeller.objects.filter(active=True, username=username).exists()


def _cooldown_key(product: MonitoredProduct, price_usd: Decimal) -> str:
    return f"{COOLDOWN_KEY_PREFIX}{product.ebay_item_id}:{price_usd:.2f}"


def _in_cooldown(product: MonitoredProduct, price_usd: Decimal) -> bool:
    return cache.get(_cooldown_key(product, price_usd)) is not None


def _set_cooldown(product: MonitoredProduct, price_usd: Decimal) -> None:
    hours = getattr(settings, 'NOTIFICATION_COOLDOWN_HOURS', 6)
    ttl = int(hours) * 3600
    cache.set(_cooldown_key(product, price_usd), '1', ttl)


def _persist_observation(
    product: MonitoredProduct,
    snapshot: EbayItemSnapshot,
    now: datetime,
    was_available: bool,
) -> None:
    fields = ['last_known_price_usd', 'last_known_seller', 'updated_at']
    product.last_known_price_usd = snapshot.price_usd
    product.last_known_seller = snapshot.seller_username
    if was_available:
        product.last_seen_available_at = now
        fields.append('last_seen_available_at')
    product.save(update_fields=fields)


def _persist_notification(product: MonitoredProduct, snapshot: EbayItemSnapshot, now: datetime) -> None:
    product.last_notified_at = now
    product.last_notified_price_usd = snapshot.price_usd
    product.save(update_fields=['last_notified_at', 'last_notified_price_usd', 'updated_at'])


@transaction.atomic
def _write_price_check(
    product: MonitoredProduct,
    outcome: CheckOutcome,
    *,
    was_available: bool,
    error_message: str = '',
) -> None:
    pc = PriceCheck.objects.create(
        monitored_product=product,
        was_available=was_available,
        price_usd=outcome.price_usd,
        trm_used=outcome.trm_used,
        price_cop_calculated=outcome.price_cop,
        seller_username=outcome.seller_username,
        seller_is_trusted=outcome.seller_is_trusted,
        triggered_notification=outcome.notified,
        error_message=error_message or outcome.error_message,
    )
    outcome.price_check_id = pc.pk
