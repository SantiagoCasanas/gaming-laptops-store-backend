from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.core.cache import cache

from deal_watcher.services import trm_cache


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_first_call_hits_db_and_caches():
    target = date(2026, 5, 8)
    fake_trm = MagicMock(valor_cop=Decimal('4123.45'))
    with patch('deal_watcher.services.trm_cache.get_trm_for_date', return_value=fake_trm) as svc:
        result = trm_cache.get_trm_value_for_date(target)
        assert result == Decimal('4123.45')
        svc.assert_called_once_with(target)

    # Second call must not hit the DB
    with patch('deal_watcher.services.trm_cache.get_trm_for_date') as svc:
        result2 = trm_cache.get_trm_value_for_date(target)
        assert result2 == Decimal('4123.45')
        svc.assert_not_called()


def test_invalidate_forces_refetch():
    target = date(2026, 5, 8)
    fake_trm = MagicMock(valor_cop=Decimal('4123.45'))
    with patch('deal_watcher.services.trm_cache.get_trm_for_date', return_value=fake_trm) as svc:
        trm_cache.get_trm_value_for_date(target)
        trm_cache.invalidate_trm_cache(target)
        trm_cache.get_trm_value_for_date(target)
        assert svc.call_count == 2


def test_propagates_value_error_when_no_trm():
    target = date(2026, 5, 8)
    with patch(
        'deal_watcher.services.trm_cache.get_trm_for_date',
        side_effect=ValueError('no trm'),
    ):
        with pytest.raises(ValueError):
            trm_cache.get_trm_value_for_date(target)
