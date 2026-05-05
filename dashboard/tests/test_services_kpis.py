"""KPI service tests — empty month, deltas, profit math, missing OC, damage origin."""

import logging
from datetime import date, datetime, timedelta, timezone as dt_tz
from decimal import Decimal

import pytest
from django.utils import timezone

from dashboard import services
from sales.models import ItemVenta

from .factories import (
    ClienteFactory,
    ItemVentaFactory,
    OrdenCompraFactory,
    ProductoFactory,
    UnidadProductoFactory,
    VentaFactory,
    force_timestamp,
    make_sold_unit,
)


def _aware(year, month, day, hour=12):
    return timezone.make_aware(datetime(year, month, day, hour))


# ---------------------------------------------------------------------------
# 1. Empty month — every KPI returns zero/None deltas, no exceptions.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_kpis_empty_month_all_zero(selected_month):
    result = services.get_kpis(selected_month)

    assert result['ventas_mes']['valor'] == Decimal('0')
    assert result['ventas_mes']['delta_pct'] is None  # both zero → None

    assert result['ganancia_neta']['valor'] == Decimal('0')
    assert result['ganancia_neta']['delta_pct'] is None

    assert result['ordenes_por_entregar'] == {'valor': 0, 'atrasadas_2_dias': 0}
    assert result['valor_inventario'] == {'valor': Decimal('0'), 'cantidad_equipos': 0}
    assert result['equipos_viajando'] == {'cantidad': 0, 'valor_en_camino': Decimal('0')}
    assert result['equipos_danados'] == {
        'total': 0,
        'estado_reparacion': {'en_reparacion': 0, 'por_reparar': 0},
        'origen_dano': {'garantia': 0, 'stock': 0},
    }


# ---------------------------------------------------------------------------
# 2. delta_pct when previous month is zero → contract: returns None.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_kpis_delta_pct_null_when_previous_zero(selected_month):
    make_sold_unit(
        precio_venta=1_000_000,
        costo_compra=400_000,
        impuesto=8_000,
        fecha_venta=_aware(selected_month.year, selected_month.month, 15),
    )
    result = services.get_kpis(selected_month)

    assert result['ventas_mes']['valor'] == Decimal('1000000')
    assert result['ventas_mes']['delta_pct'] is None  # documented contract


# ---------------------------------------------------------------------------
# 3. Multi-item profit: 3 sales in the month, distinct costs and taxes.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_kpis_ganancia_neta_multi_item(selected_month):
    fecha = _aware(selected_month.year, selected_month.month, 10)
    make_sold_unit(precio_venta=1_000_000, costo_compra=600_000, impuesto=12_000, fecha_venta=fecha)
    make_sold_unit(precio_venta=2_000_000, costo_compra=1_300_000, impuesto=26_000, fecha_venta=fecha)
    make_sold_unit(precio_venta=500_000, costo_compra=300_000, impuesto=6_000, fecha_venta=fecha)

    result = services.get_kpis(selected_month)

    # ventas = 1m + 2m + 0.5m = 3.5m
    assert result['ventas_mes']['valor'] == Decimal('3500000')
    # ganancia = (1m-600k-12k) + (2m-1.3m-26k) + (500k-300k-6k)
    #         = 388,000 + 674,000 + 194,000 = 1,256,000
    assert result['ganancia_neta']['valor'] == Decimal('1256000')


# ---------------------------------------------------------------------------
# 4. Sale whose unit has no OrdenCompra → excluded from ganancia, logged warning.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_kpis_ganancia_excludes_units_without_orden_compra(selected_month, caplog):
    fecha = _aware(selected_month.year, selected_month.month, 12)

    # Sale 1: complete chain (has OC) → should be counted
    make_sold_unit(precio_venta=1_000_000, costo_compra=400_000, impuesto=8_000, fecha_venta=fecha)

    # Sale 2: unit without OC → should be skipped from profit (but counted in ventas)
    unidad = UnidadProductoFactory(estado_venta='vendido')
    venta = VentaFactory()
    force_timestamp(venta, fecha=fecha, created_at=fecha)
    ItemVentaFactory(venta=venta, unidad_producto=unidad, precio=Decimal('900000'))

    with caplog.at_level(logging.WARNING, logger='dashboard.services'):
        result = services.get_kpis(selected_month)

    assert result['ventas_mes']['valor'] == Decimal('1900000')  # both sales counted in ventas
    # ganancia = only the first item: 1m - 400k - 8k = 592,000
    assert result['ganancia_neta']['valor'] == Decimal('592000')

    assert any('sin OrdenCompra' in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# 6. Damage origin classification.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_kpis_damage_origin_classification(selected_month):
    # Damaged unit WITH historical sale → garantia
    sold_unit = UnidadProductoFactory(estado_venta='danado', estado_producto='en_reparacion')
    venta = VentaFactory()
    ItemVentaFactory(venta=venta, unidad_producto=sold_unit, precio=Decimal('1000000'))

    # Damaged unit WITHOUT a sale → stock
    UnidadProductoFactory(estado_venta='danado', estado_producto='por_reparar')
    UnidadProductoFactory(estado_venta='danado', estado_producto='en_reparacion')

    result = services.get_kpis(selected_month)

    assert result['equipos_danados']['total'] == 3
    assert result['equipos_danados']['estado_reparacion'] == {'en_reparacion': 2, 'por_reparar': 1}
    assert result['equipos_danados']['origen_dano'] == {'garantia': 1, 'stock': 2}
