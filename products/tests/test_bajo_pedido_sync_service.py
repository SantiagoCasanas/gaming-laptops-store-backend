"""
Tests for the daily eBay Bajo Pedido sync (Hito 5).

Everything external is mocked — NO real eBay/TRM/Telegram calls:
- `get_ebay_item_data`  → patched to a sentinel dict (or raises).
- `parse_item_payload`  → patched to return a snapshot stub built per case.
- `get_trm_value_for_date` → patched to a Decimal (or raises / None).
- `send_plain_message`  → a Mock; we assert called / not called.
- `scheduler_service.record_reserve_usage` → patched; assert call count/arg.

`TrustedSeller` rows are created for real (the trust check is a DB query).
The snapshot's `seller_username` is always lowercase to mirror what the real
parser produces (`_extract_seller_username` lowercases), so it matches the
`_is_trusted` query and the `TrustedSeller.username` we seed.

All monetary assertions use `Decimal`.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings

from products.models import BajoPedido, SyncBajoPedidoLog, UnidadProducto
from products.services import bajo_pedido_sync_service as svc
from products.tests.factories import (
    BajoPedidoFactory,
    UnidadProductoFactory,
)

from deal_watcher.tests.factories import (
    TelegramSubscriberFactory,
    TrustedSellerFactory,
)

pytestmark = pytest.mark.django_db

Resultado = SyncBajoPedidoLog.ResultadoChoices
Disponibilidad = BajoPedido.DisponibilidadEbayChoices
Estado = BajoPedido.EstadoChoices

_MODULE = 'products.services.bajo_pedido_sync_service'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snapshot(*, price_usd='100', seller='goodseller', has_price=True, available=True):
    """Build a stub mirroring `EbayItemSnapshot`'s relevant attributes.

    `has_price` controls the property the service reads directly; we keep
    `price_usd`/`has_price` independent so we can test the "no usable price"
    branch without fighting the real dataclass property.
    """
    snap = MagicMock(name='EbayItemSnapshot')
    snap.price_usd = Decimal(price_usd) if price_usd is not None else None
    snap.seller_username = seller
    snap.has_price = has_price
    snap.is_available = available
    return snap


def _patch_ebay(side_effect=None):
    if side_effect is not None:
        return patch(f'{_MODULE}.get_ebay_item_data', side_effect=side_effect)
    return patch(f'{_MODULE}.get_ebay_item_data', return_value={'sentinel': True})


def _patch_parse(snapshot):
    return patch(f'{_MODULE}.parse_item_payload', return_value=snapshot)


def _patch_trm(value=Decimal('4000'), side_effect=None):
    if side_effect is not None:
        return patch(f'{_MODULE}.get_trm_value_for_date', side_effect=side_effect)
    return patch(f'{_MODULE}.get_trm_value_for_date', return_value=value)


def _patch_telegram():
    return patch(f'{_MODULE}.send_plain_message', MagicMock())


def _patch_reserve():
    return patch(f'{_MODULE}.scheduler_service.record_reserve_usage', MagicMock())


# Real-token + a real subscriber so `_broadcast_telegram` actually fires the
# (mocked) per-chat sender when a notification is warranted.
TELEGRAM_ON = override_settings(TELEGRAM_BOT_TOKEN='test-token')


# ---------------------------------------------------------------------------
# round_to / round_up_to unit checks (rounding edge support)
# ---------------------------------------------------------------------------

def test_round_up_to_never_rounds_below_target():
    # 901500 nearest-rounds DOWN to 900000 but ceiling keeps it at 990000.
    assert svc.round_to(Decimal('901500'), Decimal('90000')) == Decimal('900000')
    assert svc.round_up_to(Decimal('901500'), Decimal('90000')) == Decimal('990000')


# ===========================================================================
# CASE 1 — X = 0 (no ZeroDivisionError; price rises to B > 0)
# ===========================================================================

@TELEGRAM_ON
def test_case1_precio_cero_sube_sin_zerodivision():
    bp = BajoPedidoFactory(precio=Decimal('0'))
    TrustedSellerFactory(username='goodseller')
    TelegramSubscriberFactory(active=True)

    with _patch_ebay(), _patch_parse(_snapshot(price_usd='100')), _patch_trm(), \
            _patch_telegram() as tg, _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.precio == Decimal('720000')  # B for usd=100, trm=4000
    assert bp.precio > 0
    assert bp.disponibilidad_ebay == Disponibilidad.DISPONIBLE
    assert resumen['subidos'] == 1
    assert resumen['llamadas_ebay'] == 1
    log = SyncBajoPedidoLog.objects.get(bajo_pedido=bp)
    assert log.resultado == Resultado.PRECIO_SUBIDO
    tg.assert_called_once()  # price-up alert


# ===========================================================================
# CASE 2 — Ratchet
# ===========================================================================

@TELEGRAM_ON
def test_case2a_costo_baja_margen_sano_no_cambia_precio():
    """Cost dropped: current margin already above floor and B < X.
    Price must NOT change; result MARGEN_PARA_BAJAR; Telegram notified."""
    bp = BajoPedidoFactory(precio=Decimal('2000000'))
    TrustedSellerFactory(username='goodseller')
    TelegramSubscriberFactory(active=True)

    # usd=100 → B=720000 < X=2000000; margin@X = 72% >= 20%.
    with _patch_ebay(), _patch_parse(_snapshot(price_usd='100')), _patch_trm(), \
            _patch_telegram() as tg, _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.precio == Decimal('2000000')  # unchanged
    assert bp.disponibilidad_ebay == Disponibilidad.DISPONIBLE
    assert bp.estado == Estado.ACTIVO
    assert resumen['margen_para_bajar'] == 1
    assert resumen['subidos'] == 0
    log = SyncBajoPedidoLog.objects.get(bajo_pedido=bp)
    assert log.resultado == Resultado.MARGEN_PARA_BAJAR
    assert log.precio_anterior == Decimal('2000000')
    assert log.precio_nuevo == Decimal('2000000')
    tg.assert_called_once()  # "margen para bajar" alert


@TELEGRAM_ON
def test_case2b_margen_bajo_sube_a_B_y_margen_resultante_ok():
    """Current margin below floor → raise to B; PRECIO_SUBIDO; Telegram notified;
    realized margin at B >= MARGEN_MINIMO."""
    bp = BajoPedidoFactory(precio=Decimal('1000000'))
    TrustedSellerFactory(username='goodseller')
    TelegramSubscriberFactory(active=True)

    # usd=200 → Y=966000, B=1260000; margin@X(1M)=3.4% < 20%; margin@B=23.3%.
    with _patch_ebay(), _patch_parse(_snapshot(price_usd='200')), _patch_trm(), \
            _patch_telegram() as tg, _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.precio == Decimal('1260000')
    assert resumen['subidos'] == 1
    log = SyncBajoPedidoLog.objects.get(bajo_pedido=bp)
    assert log.resultado == Resultado.PRECIO_SUBIDO

    # Realized margin at B must be >= floor (0.20).
    Y = Decimal('966000')
    realized = (bp.precio - Y) / bp.precio
    assert realized >= Decimal('0.20')
    tg.assert_called_once()


@TELEGRAM_ON
def test_case2c_borde_redondeo_ratchet_nunca_baja():
    """Rounding edge: the unrounded target nearest-rounds DOWN below the floor,
    but ceiling (round_up_to) keeps B >= X and margin >= floor."""
    # usd=140 → Y=721200, target=901500. Nearest → 900000 (margin 19.87% < 20%),
    # ceiling → 990000 (margin 27.15%). Start at X=900000 (the nearest value).
    bp = BajoPedidoFactory(precio=Decimal('900000'))
    TrustedSellerFactory(username='goodseller')

    with _patch_ebay(), _patch_parse(_snapshot(price_usd='140')), _patch_trm(), \
            _patch_telegram(), _patch_reserve():
        svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.precio == Decimal('990000')        # ceiling, not 900000
    assert bp.precio >= Decimal('900000')        # ratchet never lowered it
    Y = Decimal('721200')
    realized = (bp.precio - Y) / bp.precio
    assert realized >= Decimal('0.20')           # floor preserved by ceiling
    log = SyncBajoPedidoLog.objects.get(bajo_pedido=bp)
    assert log.resultado == Resultado.PRECIO_SUBIDO


# ===========================================================================
# CASE 3 — Units frontier
# ===========================================================================

def test_case3a_con_unidades_skip_no_llama_ebay():
    bp = BajoPedidoFactory(
        precio=Decimal('2000000'),
        estado=Estado.ACTIVO,
        disponibilidad_ebay=Disponibilidad.DISPONIBLE,
    )
    # An active, unsold, in-stock unit for the SAME producto + condicion.
    UnidadProductoFactory(
        producto=bp.producto,
        condicion=bp.condicion,
        estado_venta=UnidadProducto.EstadoVentaChoices.SIN_VENDER,
        estado_producto=UnidadProducto.EstadoProductoChoices.EN_STOCK,
    )
    TrustedSellerFactory(username='goodseller')

    with _patch_ebay() as ebay, _patch_parse(_snapshot()), _patch_trm(), \
            _patch_telegram() as tg, _patch_reserve() as reserve:
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    ebay.assert_not_called()           # frontier: never hits eBay
    bp.refresh_from_db()
    assert bp.precio == Decimal('2000000')                 # intact
    assert bp.estado == Estado.ACTIVO                       # intact
    assert bp.disponibilidad_ebay == Disponibilidad.DISPONIBLE  # intact
    assert resumen['skip_con_unidades'] == 1
    assert resumen['llamadas_ebay'] == 0
    log = SyncBajoPedidoLog.objects.get(bajo_pedido=bp)
    assert log.resultado == Resultado.CON_UNIDADES_SKIP
    tg.assert_not_called()
    reserve.assert_not_called()        # no eBay calls → no reserve telemetry


def test_case3b_sin_unidades_si_actua_llama_ebay():
    bp = BajoPedidoFactory(precio=Decimal('2000000'))
    TrustedSellerFactory(username='goodseller')
    # No backing unit (or a unit that does NOT qualify): a sold unit.
    UnidadProductoFactory(
        producto=bp.producto,
        condicion=bp.condicion,
        estado_venta=UnidadProducto.EstadoVentaChoices.VENDIDO,
        estado_producto=UnidadProducto.EstadoProductoChoices.ENTREGADO,
    )

    with _patch_ebay() as ebay, _patch_parse(_snapshot(price_usd='100')), _patch_trm(), \
            _patch_telegram(), _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    ebay.assert_called_once()
    assert resumen['skip_con_unidades'] == 0
    assert resumen['llamadas_ebay'] == 1


# ===========================================================================
# CASE 4 — Untrusted seller
# ===========================================================================

@TELEGRAM_ON
def test_case4_seller_no_confiable_agota_y_suma_fallo():
    bp = BajoPedidoFactory(
        precio=Decimal('2000000'),
        fallos_consecutivos=0,
        disponibilidad_ebay=Disponibilidad.DISPONIBLE,
        estado=Estado.ACTIVO,
    )
    # No TrustedSeller for 'randomguy'.
    TelegramSubscriberFactory(active=True)

    with _patch_ebay(), _patch_parse(_snapshot(seller='randomguy')), _patch_trm(), \
            _patch_telegram() as tg, _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.precio == Decimal('2000000')                # unchanged
    assert bp.disponibilidad_ebay == Disponibilidad.AGOTADO
    assert bp.estado == Estado.SIN_EXISTENCIAS
    assert bp.fallos_consecutivos == 1
    assert resumen['agotados'] == 1
    log = SyncBajoPedidoLog.objects.get(bajo_pedido=bp)
    assert log.resultado == Resultado.AGOTADO_SELLER
    tg.assert_not_called()             # untrusted agotado does not notify


# ===========================================================================
# CASE 5 — Consecutive failure counter → AGOTADO_FALLOS, and reset on success
# ===========================================================================

@override_settings(FALLOS_PARA_AGOTAR=3)
def test_case5_fallos_consecutivos_agota_en_el_umbral():
    bp = BajoPedidoFactory(
        precio=Decimal('2000000'),
        fallos_consecutivos=0,
        disponibilidad_ebay=Disponibilidad.DISPONIBLE,
        estado=Estado.ACTIVO,
    )

    # Each run eBay raises (network error / not found). Before threshold the
    # state must be preserved; on the 3rd run it flips to agotado.
    for i in range(1, 3):  # runs 1 and 2 (below threshold of 3)
        with _patch_ebay(side_effect=RuntimeError('boom')), \
                _patch_parse(_snapshot()), _patch_trm(), \
                _patch_telegram(), _patch_reserve():
            svc.sync_bajo_pedido_precios_disponibilidad()
        bp.refresh_from_db()
        assert bp.fallos_consecutivos == i
        assert bp.disponibilidad_ebay == Disponibilidad.DISPONIBLE  # preserved
        assert bp.estado == Estado.ACTIVO                            # preserved

    # 3rd consecutive failure hits the threshold → agotado.
    with _patch_ebay(side_effect=RuntimeError('boom')), \
            _patch_parse(_snapshot()), _patch_trm(), \
            _patch_telegram(), _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()
    bp.refresh_from_db()
    assert bp.fallos_consecutivos == 3
    assert bp.disponibilidad_ebay == Disponibilidad.AGOTADO
    assert bp.estado == Estado.SIN_EXISTENCIAS
    assert bp.active is True            # never deactivated
    assert resumen['agotados'] == 1
    log = SyncBajoPedidoLog.objects.filter(bajo_pedido=bp).first()
    assert log.resultado == Resultado.AGOTADO_FALLOS


@override_settings(FALLOS_PARA_AGOTAR=3)
def test_case5_sync_exitoso_resetea_fallos():
    bp = BajoPedidoFactory(precio=Decimal('2000000'), fallos_consecutivos=2)
    TrustedSellerFactory(username='goodseller')

    with _patch_ebay(), _patch_parse(_snapshot(price_usd='100')), _patch_trm(), \
            _patch_telegram(), _patch_reserve():
        svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.fallos_consecutivos == 0


# ===========================================================================
# CASE 6 — TRM absent / item-not-found / network error
# ===========================================================================

@override_settings(FALLOS_PARA_AGOTAR=15)
def test_case6_trm_none_se_trata_como_fallo():
    bp = BajoPedidoFactory(
        precio=Decimal('2000000'),
        fallos_consecutivos=0,
        disponibilidad_ebay=Disponibilidad.DISPONIBLE,
        estado=Estado.ACTIVO,
    )
    TrustedSellerFactory(username='goodseller')

    with _patch_ebay(), _patch_parse(_snapshot(price_usd='100')), \
            _patch_trm(value=None), _patch_telegram(), _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.precio == Decimal('2000000')                # state kept
    assert bp.disponibilidad_ebay == Disponibilidad.DISPONIBLE
    assert bp.estado == Estado.ACTIVO
    assert bp.fallos_consecutivos == 1
    assert resumen['fallos'] == 1
    assert resumen['agotados'] == 0
    log = SyncBajoPedidoLog.objects.get(bajo_pedido=bp)
    assert log.resultado == Resultado.FALLO_EBAY


@override_settings(FALLOS_PARA_AGOTAR=15)
def test_case6_trm_raise_se_trata_como_fallo():
    bp = BajoPedidoFactory(
        precio=Decimal('2000000'),
        disponibilidad_ebay=Disponibilidad.DISPONIBLE,
        estado=Estado.ACTIVO,
    )
    TrustedSellerFactory(username='goodseller')

    with _patch_ebay(), _patch_parse(_snapshot(price_usd='100')), \
            _patch_trm(side_effect=ValueError('no trm')), \
            _patch_telegram(), _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.fallos_consecutivos == 1
    assert resumen['fallos'] == 1
    assert bp.disponibilidad_ebay == Disponibilidad.DISPONIBLE


@override_settings(FALLOS_PARA_AGOTAR=15)
def test_case6_item_no_encontrado_mantiene_estado_nunca_agotado_un_solo_fallo():
    bp = BajoPedidoFactory(
        precio=Decimal('2000000'),
        disponibilidad_ebay=Disponibilidad.DISPONIBLE,
        estado=Estado.ACTIVO,
        fallos_consecutivos=0,
    )

    with _patch_ebay(side_effect=RuntimeError('item not found')), \
            _patch_parse(_snapshot()), _patch_trm(), \
            _patch_telegram(), _patch_reserve():
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    bp.refresh_from_db()
    assert bp.precio == Decimal('2000000')                       # last price kept
    assert bp.disponibilidad_ebay == Disponibilidad.DISPONIBLE   # never agotado
    assert bp.estado == Estado.ACTIVO
    assert bp.fallos_consecutivos == 1
    assert resumen['fallos'] == 1
    assert resumen['agotados'] == 0


# ===========================================================================
# CASE 8 — Telemetry: record_reserve_usage called once with real eBay calls
# ===========================================================================

def test_case8_telemetria_reserve_usage_cuenta_solo_llamadas_reales():
    # bp1: has units → SKIP (no eBay call). bp2 + bp3: real eBay calls.
    bp1 = BajoPedidoFactory(precio=Decimal('2000000'))
    UnidadProductoFactory(
        producto=bp1.producto,
        condicion=bp1.condicion,
        estado_venta=UnidadProducto.EstadoVentaChoices.SIN_VENDER,
        estado_producto=UnidadProducto.EstadoProductoChoices.EN_STOCK,
    )
    BajoPedidoFactory(precio=Decimal('2000000'))
    BajoPedidoFactory(precio=Decimal('2000000'))
    TrustedSellerFactory(username='goodseller')

    with _patch_ebay(), _patch_parse(_snapshot(price_usd='100')), _patch_trm(), \
            _patch_telegram(), _patch_reserve() as reserve:
        resumen = svc.sync_bajo_pedido_precios_disponibilidad()

    assert resumen['skip_con_unidades'] == 1
    assert resumen['llamadas_ebay'] == 2      # only the 2 unit-less listings
    reserve.assert_called_once_with(2)
