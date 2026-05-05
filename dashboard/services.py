"""
Dashboard query layer. Pure functions — no HTTP/DRF concerns.

Each public function takes the selected month as a `date` (always day=1) and
returns plain Python dicts/lists ready for JSON serialization.

Query optimization: every function aims for the minimum number of round trips.
`get_kpis` is bounded to 6 queries.
"""

from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import (
    Case,
    Count,
    DecimalField,
    Exists,
    F,
    OuterRef,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from core.models import TRMHistory
from products.models import UnidadProducto
from purchases.models import OrdenCompra
from sales.models import ItemVenta, Separacion, Venta

from .exceptions import InvalidMonthParam

logger = logging.getLogger(__name__)

ZERO = Decimal('0')
ATRASADAS_THRESHOLD_DAYS = 2
_MONTH_RE = re.compile(r'^\d{4}-\d{2}$')  # strict YYYY-MM with zero-padding


def _get_active_trm() -> Decimal:
    """
    Returns the most recent TRM (USD→COP) value. Used to convert OrdenCompra
    monetary fields (stored in USD) to COP for dashboard responses. If no TRM
    is loaded (e.g. fresh DB or test env), returns 1 — values stay in USD.
    """
    latest = TRMHistory.objects.only('valor_cop').order_by('-fecha').first()
    return latest.valor_cop if latest else Decimal('1')


# ----------------------------------------------------------------------------
# Date helpers
# ----------------------------------------------------------------------------

def parse_month_param(request) -> date:
    """
    Read ?month=YYYY-MM from the request. Returns the first day of that month.
    If the param is missing/empty, defaults to the first day of the current month.
    Raises InvalidMonthParam (HTTP 400) on malformed input.
    """
    raw = request.query_params.get('month') if hasattr(request, 'query_params') else None
    if raw is None or raw == '':
        today = timezone.localdate()
        return today.replace(day=1)
    if not _MONTH_RE.match(raw):
        raise InvalidMonthParam()
    try:
        parsed = datetime.strptime(raw, '%Y-%m').date()
    except (ValueError, TypeError):
        raise InvalidMonthParam()
    return parsed.replace(day=1)


def month_range(month: date) -> tuple[date, date]:
    """Return [first_day, first_day_of_next_month) for the given month."""
    first = month.replace(day=1)
    if first.month == 12:
        nxt = date(first.year + 1, 1, 1)
    else:
        nxt = date(first.year, first.month + 1, 1)
    return first, nxt


def _aware_bounds(month: date) -> tuple[datetime, datetime]:
    """Aware-datetime bounds for DateTimeField filters — silences naive warnings."""
    start, end = month_range(month)
    return (
        timezone.make_aware(datetime.combine(start, datetime.min.time())),
        timezone.make_aware(datetime.combine(end, datetime.min.time())),
    )


def previous_month(month: date) -> date:
    """First day of the month before `month`."""
    first = month.replace(day=1)
    if first.month == 1:
        return date(first.year - 1, 12, 1)
    return date(first.year, first.month - 1, 1)


def _delta_pct(current, previous) -> Optional[float]:
    """
    Percentage change vs previous. Returns None when previous is zero/null
    (frontend renders "—" in that case).
    """
    current = Decimal(current or 0)
    previous = Decimal(previous or 0)
    if previous == 0:
        return None
    return float(((current - previous) / previous) * 100)


# ----------------------------------------------------------------------------
# Query helpers — kept private; public endpoints below.
# ----------------------------------------------------------------------------

def _aggregate_sales_for_range(start: date, end: date, trm: Decimal) -> dict:
    """
    Walk every ItemVenta whose Venta.fecha falls in [start, end), pre-fetching
    the linked UnidadProducto.orden_compra. Returns ventas + ganancia in COP
    in one pass (one query). All inputs are now in COP — costo_compra,
    impuesto_importacion and costo_importacion all live in COP, no TRM
    conversion is needed. The `trm` parameter is kept for backwards
    compatibility but is not consumed for the cost legs.
    """
    aware_start, aware_end = (
        timezone.make_aware(datetime.combine(start, datetime.min.time())),
        timezone.make_aware(datetime.combine(end, datetime.min.time())),
    )
    items = (
        ItemVenta.objects
        .filter(venta__fecha__gte=aware_start, venta__fecha__lt=aware_end)
        .select_related('unidad_producto__orden_compra')
    )

    ventas = ZERO
    ganancia = ZERO
    for item in items:
        precio = item.precio or ZERO  # already COP
        ventas += precio
        oc = getattr(item.unidad_producto, 'orden_compra', None)
        if oc is None:
            logger.warning(
                "ganancia_neta: ItemVenta id=%s (unidad=%s) sin OrdenCompra; excluido",
                item.pk, item.unidad_producto_id,
            )
            continue
        costo = oc.costo_compra or ZERO
        impuesto = oc.impuesto_importacion or ZERO
        importacion = oc.costo_importacion or ZERO
        ganancia += precio - costo - impuesto - importacion

    return {'ventas': ventas, 'ganancia': ganancia}


# ----------------------------------------------------------------------------
# Endpoint 1 — KPIs
# ----------------------------------------------------------------------------

def get_kpis(month: date) -> dict:
    """
    Six KPIs in ≤6 queries:
      1. ItemVenta sums for current month (ventas + ganancia)
      2. ItemVenta sums for previous month (deltas)
      3. Venta pending deliveries (total + atrasadas)
      4. UnidadProducto inventory aggregate
      5. OrdenCompra in transit aggregate
      6. UnidadProducto damaged aggregate (with Exists for origin)
    """
    start, end = month_range(month)
    prev_start, prev_end = month_range(previous_month(month))
    trm = _get_active_trm()

    # Q1 + Q2 — sales/profit current + previous (USD costs → COP via TRM)
    current = _aggregate_sales_for_range(start, end, trm)
    previous = _aggregate_sales_for_range(prev_start, prev_end, trm)

    # Q3 — pending sale deliveries (global, not month-filtered)
    cutoff = timezone.now() - timedelta(days=ATRASADAS_THRESHOLD_DAYS)
    pendientes = Venta.objects.filter(estado_entrega='por_entregar').aggregate(
        total=Count('id'),
        atrasadas=Count('id', filter=Q(fecha__lt=cutoff)),
    )

    # Q4 — inventory value
    inventario = UnidadProducto.objects.filter(
        estado_venta='sin_vender',
        estado_producto='en_stock',
    ).aggregate(
        valor=Coalesce(Sum('precio'), ZERO, output_field=DecimalField(max_digits=20, decimal_places=2)),
        cantidad=Count('id'),
    )

    # Q5 — units in transit (purchase orders) for the selected month, scoped by
    # fecha_compra. All cost legs are stored in COP, so no TRM conversion is
    # required.
    viajando = OrdenCompra.objects.filter(
        estado_logistico='viajando',
        fecha_compra__gte=start, fecha_compra__lt=end,
    ).aggregate(
        cantidad=Count('id'),
        valor_cop=Coalesce(
            Sum(
                F('costo_compra')
                + F('impuesto_importacion')
                + Coalesce(F('costo_importacion'), Decimal('0')),
            ),
            ZERO,
            output_field=DecimalField(max_digits=20, decimal_places=2),
        ),
    )
    viajando_valor_cop = viajando['valor_cop'] or ZERO

    # Q6 — damaged units. Origin via Exists subquery on ItemVenta.
    has_sale = Exists(ItemVenta.objects.filter(unidad_producto=OuterRef('pk')))
    danados = (
        UnidadProducto.objects.filter(estado_venta='danado')
        .annotate(has_sale=has_sale)
        .aggregate(
            total=Count('id'),
            en_reparacion=Count('id', filter=Q(estado_producto='en_reparacion')),
            por_reparar=Count('id', filter=Q(estado_producto='por_reparar')),
            origen_garantia=Count('id', filter=Q(has_sale=True)),
            origen_stock=Count('id', filter=Q(has_sale=False)),
        )
    )

    return {
        'ventas_mes': {
            'valor': current['ventas'],
            'delta_pct': _delta_pct(current['ventas'], previous['ventas']),
        },
        'ganancia_neta': {
            'valor': current['ganancia'],
            'delta_pct': _delta_pct(current['ganancia'], previous['ganancia']),
        },
        'ordenes_por_entregar': {
            'valor': pendientes['total'] or 0,
            'atrasadas_2_dias': pendientes['atrasadas'] or 0,
        },
        'valor_inventario': {
            'valor': inventario['valor'],
            'cantidad_equipos': inventario['cantidad'] or 0,
        },
        'equipos_viajando': {
            'cantidad': viajando['cantidad'] or 0,
            'valor_en_camino': viajando_valor_cop,
        },
        'equipos_danados': {
            'total': danados['total'] or 0,
            'estado_reparacion': {
                'en_reparacion': danados['en_reparacion'] or 0,
                'por_reparar': danados['por_reparar'] or 0,
            },
            'origen_dano': {
                'garantia': danados['origen_garantia'] or 0,
                'stock': danados['origen_stock'] or 0,
            },
        },
    }


# ----------------------------------------------------------------------------
# Endpoint 2 — Sales timeline
# ----------------------------------------------------------------------------

def _timeline_for_month(month: date) -> list[dict]:
    """Return a list with one entry per day-of-month in the given month."""
    start, end = month_range(month)
    aware_start, aware_end = _aware_bounds(month)
    rows = (
        ItemVenta.objects
        .filter(venta__fecha__gte=aware_start, venta__fecha__lt=aware_end)
        .annotate(day=TruncDate('venta__fecha'))
        .values('day')
        .annotate(valor=Sum('precio'))
    )
    by_day = {r['day'].day: (r['valor'] or ZERO) for r in rows}
    days_in_month = calendar.monthrange(month.year, month.month)[1]
    return [
        {'dia': d, 'valor': by_day.get(d, ZERO)}
        for d in range(1, days_in_month + 1)
    ]


def get_sales_timeline(month: date) -> dict:
    """Daily sales totals for the selected month and the previous one."""
    return {
        'actual': _timeline_for_month(month),
        'anterior': _timeline_for_month(previous_month(month)),
    }


# ----------------------------------------------------------------------------
# Endpoint 3 — Sales orders by delivery status (month-filtered)
# ----------------------------------------------------------------------------

def get_sales_orders_status(month: date) -> dict:
    aware_start, aware_end = _aware_bounds(month)
    agg = Venta.objects.filter(fecha__gte=aware_start, fecha__lt=aware_end).aggregate(
        por_entregar=Count('id', filter=Q(estado_entrega='por_entregar')),
        entregado=Count('id', filter=Q(estado_entrega='entregado')),
    )
    return {
        'por_entregar': agg['por_entregar'] or 0,
        'entregado': agg['entregado'] or 0,
    }


# ----------------------------------------------------------------------------
# Endpoint 4 — Purchase orders by logistic status (month-filtered)
# ----------------------------------------------------------------------------

def get_purchase_orders_status(month: date) -> dict:
    start, end = month_range(month)
    agg = OrdenCompra.objects.filter(
        fecha_compra__gte=start, fecha_compra__lt=end,
    ).aggregate(
        viajando=Count('id', filter=Q(estado_logistico='viajando')),
        en_oficina_importadora=Count('id', filter=Q(estado_logistico='en_oficina_importadora')),
        en_oficina=Count('id', filter=Q(estado_logistico='en_oficina')),
    )
    return {
        'viajando': agg['viajando'] or 0,
        'en_oficina_importadora': agg['en_oficina_importadora'] or 0,
        'en_oficina': agg['en_oficina'] or 0,
    }


# ----------------------------------------------------------------------------
# Endpoint 5 — Active reservations
# ----------------------------------------------------------------------------

def get_reservations() -> list[dict]:
    """
    All active separations without a linked sale, ordered by days held desc.
    Not month-filtered — reservations are a global state.
    """
    now = timezone.now()
    seps = (
        Separacion.objects
        .filter(estado='activa', ventas__isnull=True)
        .select_related(
            'cliente',
            'unidad_producto',
            'unidad_producto__producto__tipo_producto',
        )
        .order_by('created_at')  # oldest first → highest dias first
    )
    out = []
    for sep in seps:
        unidad = sep.unidad_producto
        producto = getattr(unidad, 'producto', None)
        tipo = getattr(producto, 'tipo_producto', None)
        out.append({
            'tipo': tipo.nombre if tipo else None,
            'serial': unidad.serial if unidad else None,
            'cliente': sep.cliente.nombre_completo if sep.cliente else None,
            'dias': (now - sep.created_at).days,
        })
    return out


# ----------------------------------------------------------------------------
# Endpoint 6 — Imports & expenses (last 6 months)
# ----------------------------------------------------------------------------

def _months_back(month: date, n: int) -> list[date]:
    """Return n consecutive month-firsts ending at `month` (inclusive), oldest first."""
    out = []
    cursor = month.replace(day=1)
    for _ in range(n):
        out.append(cursor)
        cursor = previous_month(cursor)
    return list(reversed(out))


def get_imports_expenses(month: date, lookback: int = 6) -> list[dict]:
    """
    Last `lookback` months (including selected) of import costs + tax, in COP.
    All OrdenCompra cost legs are stored in COP — no TRM conversion needed.
    """
    months = _months_back(month, lookback)
    window_start = months[0]
    _, window_end = month_range(months[-1])

    rows = (
        OrdenCompra.objects
        .filter(fecha_compra__gte=window_start, fecha_compra__lt=window_end)
        .annotate(mes=TruncMonth('fecha_compra'))
        .values('mes')
        .annotate(
            valor_importacion=Sum('costo_compra'),
            impuesto=Sum('impuesto_importacion'),
        )
    )
    by_month = {
        r['mes'].strftime('%Y-%m'): r for r in rows if r['mes'] is not None
    }

    return [
        {
            'mes': m.strftime('%Y-%m'),
            'valor_importacion': by_month.get(m.strftime('%Y-%m'), {}).get('valor_importacion') or ZERO,
            'impuesto': by_month.get(m.strftime('%Y-%m'), {}).get('impuesto') or ZERO,
        }
        for m in months
    ]
