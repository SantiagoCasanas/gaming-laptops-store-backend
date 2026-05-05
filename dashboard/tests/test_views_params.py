"""?month= parsing — well-formed, missing, malformed, out-of-range values."""

from datetime import date

import pytest
from django.urls import reverse

from dashboard import services
from dashboard.exceptions import InvalidMonthParam


class _FakeRequest:
    def __init__(self, raw=None):
        self.query_params = {} if raw is None else {'month': raw}


def test_parse_month_missing_returns_current_month():
    today = date.today()
    assert services.parse_month_param(_FakeRequest()) == today.replace(day=1)


def test_parse_month_well_formed():
    assert services.parse_month_param(_FakeRequest('2026-04')) == date(2026, 4, 1)


@pytest.mark.parametrize('bad', ['foo', '2026-13', '2026/04', '2026', '04-2026', '2026-1', ''])
def test_parse_month_malformed_raises(bad):
    if bad == '':
        # empty is treated as missing → defaults to today; not an error.
        services.parse_month_param(_FakeRequest(bad))
        return
    with pytest.raises(InvalidMonthParam):
        services.parse_month_param(_FakeRequest(bad))


@pytest.mark.django_db
def test_view_returns_400_on_invalid_month(admin_client):
    resp = admin_client.get(reverse('dashboard:kpis'), {'month': 'foo'})
    assert resp.status_code == 400
    assert 'month' in resp.json()


@pytest.mark.django_db
def test_view_returns_400_on_out_of_range_month(admin_client):
    resp = admin_client.get(reverse('dashboard:kpis'), {'month': '2026-13'})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_view_accepts_valid_month(admin_client):
    resp = admin_client.get(reverse('dashboard:kpis'), {'month': '2026-04'})
    assert resp.status_code == 200
