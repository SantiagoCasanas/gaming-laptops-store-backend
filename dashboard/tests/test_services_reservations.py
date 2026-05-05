"""Reservations endpoint — boundary days + ordering."""

import pytest

from dashboard import services

from .factories import make_separacion


@pytest.mark.django_db
def test_reservations_borders_and_ordering():
    # Create separations at the requested day-deltas. Order desc by dias.
    expected_days = [0, 15, 16, 25, 26, 30]
    for d in expected_days:
        make_separacion(dias_atras=d)

    result = services.get_reservations()

    assert len(result) == len(expected_days)
    # Sorted by oldest first → highest dias first.
    days_returned = [row['dias'] for row in result]
    assert days_returned == sorted(expected_days, reverse=True)


@pytest.mark.django_db
def test_reservations_excludes_completed_and_with_sale():
    """Cancelled/completed separations and active+with-sale separations are excluded."""
    from .factories import SeparacionFactory, VentaFactory, force_timestamp
    from datetime import timedelta
    from django.utils import timezone

    # Active without sale → included
    active = SeparacionFactory()
    force_timestamp(active, created_at=timezone.now() - timedelta(days=5))

    # Cancelled → excluded
    cancelled = SeparacionFactory(estado='cancelada')
    force_timestamp(cancelled, created_at=timezone.now() - timedelta(days=10))

    # Active but already linked to a Venta → excluded
    linked = SeparacionFactory()
    force_timestamp(linked, created_at=timezone.now() - timedelta(days=20))
    VentaFactory(cliente=linked.cliente, separacion=linked)

    result = services.get_reservations()
    serials = [r['serial'] for r in result]

    assert active.unidad_producto.serial in serials
    assert cancelled.unidad_producto.serial not in serials
    assert linked.unidad_producto.serial not in serials


@pytest.mark.django_db
def test_reservations_empty():
    assert services.get_reservations() == []
