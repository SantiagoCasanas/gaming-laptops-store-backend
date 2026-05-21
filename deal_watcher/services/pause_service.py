"""
Pause resolution. A monitored product is paused when:

- there exists an active global pause whose `paused_until` is null or in the future, OR
- there exists an active per-product pause for that product matching the same window.

`active=False` rows (deactivated) are ignored, even if `paused_until` is in
the future. This lets the operator cancel an indefinite pause by toggling the
`active` flag.
"""
from datetime import datetime
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from deal_watcher.models import MonitoredProduct, NotificationPause


def _active_pause_filter(now: datetime) -> Q:
    return Q(active=True) & (Q(paused_until__isnull=True) | Q(paused_until__gt=now))


def is_globally_paused(now: Optional[datetime] = None) -> bool:
    now = now or timezone.now()
    return NotificationPause.objects.filter(
        _active_pause_filter(now),
        scope=NotificationPause.SCOPE_GLOBAL,
    ).exists()


def is_product_paused(product: MonitoredProduct, now: Optional[datetime] = None) -> bool:
    """True if either the global pause or a pause for this product is active."""
    now = now or timezone.now()
    if is_globally_paused(now):
        return True
    return NotificationPause.objects.filter(
        _active_pause_filter(now),
        scope=NotificationPause.SCOPE_PRODUCT,
        monitored_product=product,
    ).exists()


def get_active_global_pause(now: Optional[datetime] = None) -> Optional[NotificationPause]:
    now = now or timezone.now()
    return (
        NotificationPause.objects
        .filter(_active_pause_filter(now), scope=NotificationPause.SCOPE_GLOBAL)
        .order_by('-created_at')
        .first()
    )


def get_active_product_pauses(now: Optional[datetime] = None):
    """Active per-product pauses, newest first, with `monitored_product` preloaded."""
    now = now or timezone.now()
    return (
        NotificationPause.objects
        .filter(_active_pause_filter(now), scope=NotificationPause.SCOPE_PRODUCT)
        .select_related('monitored_product')
        .order_by('-created_at')
    )


def create_global_pause(
    *,
    paused_until: Optional[datetime],
    reason: str = '',
    created_via: str = NotificationPause.CREATED_VIA_UI,
) -> NotificationPause:
    return NotificationPause.objects.create(
        scope=NotificationPause.SCOPE_GLOBAL,
        monitored_product=None,
        paused_until=paused_until,
        reason=reason,
        created_via=created_via,
    )


def create_product_pause(
    *,
    product: MonitoredProduct,
    paused_until: Optional[datetime],
    reason: str = '',
    created_via: str = NotificationPause.CREATED_VIA_UI,
) -> NotificationPause:
    return NotificationPause.objects.create(
        scope=NotificationPause.SCOPE_PRODUCT,
        monitored_product=product,
        paused_until=paused_until,
        reason=reason,
        created_via=created_via,
    )


def deactivate_active_pauses(*, scope: Optional[str] = None, product: Optional[MonitoredProduct] = None) -> int:
    """
    Deactivate every currently-active pause matching the filter.
    Used when the operator clicks 'Reanudar'. Returns rows updated.
    """
    qs = NotificationPause.objects.filter(active=True)
    if scope is not None:
        qs = qs.filter(scope=scope)
    if product is not None:
        qs = qs.filter(monitored_product=product)
    return qs.update(active=False)
