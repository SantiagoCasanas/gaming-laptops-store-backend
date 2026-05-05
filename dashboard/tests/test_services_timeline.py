"""Timeline + status endpoints — empty + populated cases."""

import calendar
from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from dashboard import services

from .factories import (
    OrdenCompraFactory,
    UnidadProductoFactory,
    VentaFactory,
    force_timestamp,
    make_sold_unit,
)


def _aware(year, month, day, hour=12):
    return timezone.make_aware(datetime(year, month, day, hour))


@pytest.mark.django_db
def test_timeline_empty_month_returns_full_zero_range(selected_month):
    result = services.get_sales_timeline(selected_month)
    days_in_month = calendar.monthrange(selected_month.year, selected_month.month)[1]

    assert len(result['actual']) == days_in_month
    assert all(r['valor'] == Decimal('0') for r in result['actual'])
    assert all(r['dia'] == i + 1 for i, r in enumerate(result['actual']))
    assert len(result['anterior']) > 0


@pytest.mark.django_db
def test_timeline_aggregates_per_day(selected_month):
    make_sold_unit(precio_venta=500_000, costo_compra=200_000, impuesto=4_000,
                   fecha_venta=_aware(selected_month.year, selected_month.month, 5))
    make_sold_unit(precio_venta=300_000, costo_compra=100_000, impuesto=2_000,
                   fecha_venta=_aware(selected_month.year, selected_month.month, 5))
    make_sold_unit(precio_venta=1_000_000, costo_compra=600_000, impuesto=12_000,
                   fecha_venta=_aware(selected_month.year, selected_month.month, 20))

    result = services.get_sales_timeline(selected_month)
    by_day = {r['dia']: r['valor'] for r in result['actual']}

    assert by_day[5] == Decimal('800000')
    assert by_day[20] == Decimal('1000000')
    assert by_day[1] == Decimal('0')


@pytest.mark.django_db
def test_sales_orders_status_counts_by_state(selected_month):
    # Two delivered, one pending — all in selected month
    fecha = _aware(selected_month.year, selected_month.month, 10)
    for _ in range(2):
        v = VentaFactory(estado_entrega='entregado')
        force_timestamp(v, fecha=fecha)
    v = VentaFactory(estado_entrega='por_entregar')
    force_timestamp(v, fecha=fecha)

    # One sale outside the month — must NOT be counted
    out = VentaFactory(estado_entrega='entregado')
    force_timestamp(out, fecha=_aware(selected_month.year - 1, 1, 5))

    result = services.get_sales_orders_status(selected_month)
    assert result == {'por_entregar': 1, 'entregado': 2}


@pytest.mark.django_db
def test_purchase_orders_status_counts_by_state(selected_month):
    fecha = selected_month.replace(day=12)
    OrdenCompraFactory(estado_logistico='viajando', fecha_compra=fecha)
    OrdenCompraFactory(estado_logistico='viajando', fecha_compra=fecha)
    OrdenCompraFactory(estado_logistico='en_oficina', fecha_compra=fecha)
    # Out of month
    OrdenCompraFactory(estado_logistico='viajando', fecha_compra=selected_month.replace(year=selected_month.year - 1))

    result = services.get_purchase_orders_status(selected_month)
    assert result == {'viajando': 2, 'en_oficina_importadora': 0, 'en_oficina': 1}


@pytest.mark.django_db
def test_imports_expenses_returns_six_months_padded(selected_month):
    # One order in selected month, one two months earlier
    OrdenCompraFactory(
        costo_compra=Decimal('100000'),
        fecha_compra=selected_month.replace(day=15),
    )
    two_back = services.previous_month(services.previous_month(selected_month))
    OrdenCompraFactory(
        costo_compra=Decimal('200000'),
        fecha_compra=two_back.replace(day=10),
    )

    result = services.get_imports_expenses(selected_month)

    assert len(result) == 6
    months = [row['mes'] for row in result]
    assert months[-1] == selected_month.strftime('%Y-%m')

    by_month = {r['mes']: r for r in result}
    assert by_month[selected_month.strftime('%Y-%m')]['valor_importacion'] == Decimal('100000')
    assert by_month[two_back.strftime('%Y-%m')]['valor_importacion'] == Decimal('200000')

    # All other months padded with zeros
    other_months = [m for m in months
                    if m not in {selected_month.strftime('%Y-%m'), two_back.strftime('%Y-%m')}]
    for m in other_months:
        assert by_month[m]['valor_importacion'] == Decimal('0')
        assert by_month[m]['impuesto'] == Decimal('0')
