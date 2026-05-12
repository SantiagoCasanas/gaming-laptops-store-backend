"""
Pure helpers that parse the eBay Browse API payload returned by
`products.services.ebay_service.get_ebay_item_data`.

Kept separate from any I/O so they can be unit-tested with fixture dicts.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional


@dataclass
class EbayItemSnapshot:
    """Subset of Browse API payload that Deal Watcher cares about."""
    price_usd: Optional[Decimal]
    seller_username: str
    is_available: bool
    available_quantity: Optional[int]
    condition: str

    @property
    def has_price(self) -> bool:
        return self.price_usd is not None and self.price_usd > 0


# eBay Browse API status codes that mean "buyable right now". We accept both
# the canonical `estimatedAvailabilityStatus` enum (IN_STOCK, LIMITED_STOCK,
# OUT_OF_STOCK) and the older/alternate `availabilityStatus` strings just in
# case eBay returns them for some marketplaces.
_AVAILABLE_STATUSES = {
    'in_stock',
    'limited_stock',
    'available_for_purchase',
    'available',
}


def parse_item_payload(payload: dict) -> EbayItemSnapshot:
    """
    Extract the fields Deal Watcher needs from the eBay item payload.

    Resilient to missing keys: anything not present is returned as None / ''.
    Currency is asserted to be USD; a non-USD price is treated as missing
    (Browse API can return GBP for some marketplaces).
    """
    if not isinstance(payload, dict):
        raise ValueError("eBay payload must be a dict")

    price_usd = _extract_usd_price(payload.get('price'))
    seller_username = _extract_seller_username(payload.get('seller'))
    is_available, qty = _extract_availability(payload.get('estimatedAvailabilities'))
    condition = (payload.get('condition') or '').strip()

    return EbayItemSnapshot(
        price_usd=price_usd,
        seller_username=seller_username,
        is_available=is_available,
        available_quantity=qty,
        condition=condition,
    )


def _extract_usd_price(price_obj) -> Optional[Decimal]:
    if not isinstance(price_obj, dict):
        return None
    currency = (price_obj.get('currency') or '').upper()
    if currency and currency != 'USD':
        return None
    raw = price_obj.get('value')
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return value if value > 0 else None


def _extract_seller_username(seller_obj) -> str:
    if not isinstance(seller_obj, dict):
        return ''
    return (seller_obj.get('username') or '').strip().lower()


def _extract_availability(availabilities) -> tuple[bool, Optional[int]]:
    if not isinstance(availabilities, list) or not availabilities:
        return False, None
    first = availabilities[0]
    if not isinstance(first, dict):
        return False, None
    # The canonical Browse API field is `estimatedAvailabilityStatus`.
    # `availabilityStatus` is kept as a fallback for older/alternate payloads.
    status = (
        first.get('estimatedAvailabilityStatus')
        or first.get('availabilityStatus')
        or ''
    ).lower()
    is_available = status in _AVAILABLE_STATUSES
    qty = first.get('estimatedAvailableQuantity')
    if not isinstance(qty, int):
        qty = None
    # An empty quantity overrides a positive status flag — defensive.
    if is_available and qty == 0:
        is_available = False
    return is_available, qty
