"""Shared fixtures for the dashboard test suite."""

from datetime import date

import pytest
from rest_framework.test import APIClient

from .factories import AdminUserFactory, RegularUserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return AdminUserFactory()


@pytest.fixture
def regular_user(db):
    return RegularUserFactory()


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def regular_client(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def selected_month():
    """Anchor month used across tests — pick a month that's safely in the past."""
    return date(2026, 3, 1)
