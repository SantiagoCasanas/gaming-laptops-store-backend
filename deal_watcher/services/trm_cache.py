"""
Thin Redis cache layer in front of `core.services.trm_service.get_trm_for_date`.

The DB lookup is cheap, but with N monitored products checked in the same run
we want to hit Redis once instead of the DB N times. Cache key is the ISO date,
TTL configurable via TRM_CACHE_TTL_SECONDS (default 6 h).
"""
from datetime import date as date_type
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache

from core.services.trm_service import get_trm_for_date


CACHE_KEY_PREFIX = 'deal_watcher:trm:'


def _cache_key(target_date: date_type) -> str:
    return f"{CACHE_KEY_PREFIX}{target_date.isoformat()}"


def get_trm_value_for_date(target_date: date_type) -> Decimal:
    """
    Return the COP-per-USD value for `target_date` as a Decimal.

    Uses Redis when available; falls back to a direct DB call. Raises
    `ValueError` (propagated from the underlying service) when no TRM exists
    for that date or earlier.
    """
    key = _cache_key(target_date)
    cached = cache.get(key)
    if cached is not None:
        return Decimal(str(cached))

    trm = get_trm_for_date(target_date)
    value = Decimal(str(trm.valor_cop))

    ttl = getattr(settings, 'TRM_CACHE_TTL_SECONDS', 21600)
    cache.set(key, str(value), ttl)
    return value


def invalidate_trm_cache(target_date: date_type) -> None:
    cache.delete(_cache_key(target_date))
