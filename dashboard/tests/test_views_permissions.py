"""Permission gate — only IsAdminUser can access dashboard endpoints."""

import pytest
from django.urls import reverse


ENDPOINTS = [
    'dashboard:kpis',
    'dashboard:sales-timeline',
    'dashboard:sales-orders-status',
    'dashboard:purchase-orders-status',
    'dashboard:reservations',
    'dashboard:imports-expenses',
]


@pytest.mark.django_db
@pytest.mark.parametrize('view_name', ENDPOINTS)
def test_anonymous_user_is_rejected(api_client, view_name):
    resp = api_client.get(reverse(view_name))
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
@pytest.mark.parametrize('view_name', ENDPOINTS)
def test_regular_user_is_forbidden(regular_client, view_name):
    resp = regular_client.get(reverse(view_name))
    assert resp.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize('view_name', ENDPOINTS)
def test_admin_user_is_allowed(admin_client, view_name):
    resp = admin_client.get(reverse(view_name))
    assert resp.status_code == 200
