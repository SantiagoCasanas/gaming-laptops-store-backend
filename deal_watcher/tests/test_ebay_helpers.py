from decimal import Decimal

import pytest

from deal_watcher.services.ebay_helpers import parse_item_payload


def _payload(**overrides):
    base = {
        'price': {'value': '560.00', 'currency': 'USD'},
        'seller': {'username': 'antonline'},
        'estimatedAvailabilities': [
            {'estimatedAvailabilityStatus': 'IN_STOCK', 'estimatedAvailableQuantity': 3},
        ],
        'condition': 'Manufacturer Refurbished',
    }
    base.update(overrides)
    return base


def test_happy_path_parses_all_fields():
    snap = parse_item_payload(_payload())
    assert snap.price_usd == Decimal('560.00')
    assert snap.seller_username == 'antonline'
    assert snap.is_available is True
    assert snap.available_quantity == 3
    assert snap.condition == 'Manufacturer Refurbished'
    assert snap.has_price


def test_seller_username_is_lowercased_and_stripped():
    snap = parse_item_payload(_payload(seller={'username': '  ANTONLINE  '}))
    assert snap.seller_username == 'antonline'


def test_non_usd_price_returns_none():
    snap = parse_item_payload(_payload(price={'value': '500', 'currency': 'GBP'}))
    assert snap.price_usd is None
    assert not snap.has_price


def test_zero_or_negative_price_returns_none():
    snap = parse_item_payload(_payload(price={'value': '0', 'currency': 'USD'}))
    assert snap.price_usd is None


def test_missing_price_field_is_safe():
    payload = _payload()
    payload.pop('price')
    snap = parse_item_payload(payload)
    assert snap.price_usd is None


def test_unavailable_status_is_detected():
    snap = parse_item_payload(_payload(
        estimatedAvailabilities=[{'estimatedAvailabilityStatus': 'OUT_OF_STOCK', 'estimatedAvailableQuantity': 0}],
    ))
    assert snap.is_available is False
    assert snap.available_quantity == 0


def test_limited_stock_is_treated_as_available():
    snap = parse_item_payload(_payload(
        estimatedAvailabilities=[{'estimatedAvailabilityStatus': 'LIMITED_STOCK', 'estimatedAvailableQuantity': 1}],
    ))
    assert snap.is_available is True


def test_legacy_availability_status_field_is_supported_as_fallback():
    snap = parse_item_payload(_payload(
        estimatedAvailabilities=[{'availabilityStatus': 'AVAILABLE_FOR_PURCHASE'}],
    ))
    assert snap.is_available is True


def test_zero_quantity_overrides_positive_status():
    snap = parse_item_payload(_payload(
        estimatedAvailabilities=[{'estimatedAvailabilityStatus': 'IN_STOCK', 'estimatedAvailableQuantity': 0}],
    ))
    assert snap.is_available is False


def test_missing_availability_array_is_safe():
    payload = _payload()
    payload.pop('estimatedAvailabilities')
    snap = parse_item_payload(payload)
    assert snap.is_available is False
    assert snap.available_quantity is None


def test_missing_seller_returns_empty_string():
    payload = _payload()
    payload.pop('seller')
    snap = parse_item_payload(payload)
    assert snap.seller_username == ''


def test_invalid_payload_type_raises():
    with pytest.raises(ValueError):
        parse_item_payload("not a dict")
