"""
Daily eBay price & availability sync for `BajoPedido` listings (Hito 3).

For every active listing that points to eBay we:
  1. Skip it entirely if there are real physical units backing it (the
     "¿tiene unidades?" frontier) — we never touch a listing that is fed by
     `UnidadProducto` rows; those are priced/managed elsewhere.
  2. Otherwise we hit the eBay Browse API and apply the decision matrix:
       - lookup failure / no price        → keep state, +1 fallo (AGOTADO_FALLOS
                                             only once `fallos >= FALLOS_PARA_AGOTAR`)
       - untrusted seller                 → agotado immediately, +1 fallo
       - trusted + out-of-stock           → agotado, reset fallos
       - trusted + available              → ratchet price up, reset fallos
  3. The price ratchet only ever raises the price (margin protection); when the
     underlying cost drops we notify "margen para bajar" but never lower it
     automatically.

Heavy logic lives here only. The management command (Hito 4) just calls
`sync_bajo_pedido_precios_disponibilidad()`.

Coupling note: importing helpers from `deal_watcher` is intentional and safe
(there is no import cycle products ⇄ deal_watcher at module import time).
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from typing import Optional

from django.conf import settings
from django.utils import timezone

from products.models import BajoPedido, UnidadProducto, SyncBajoPedidoLog
from products.services.ebay_service import (
    get_ebay_item_data,
    extract_legacy_id_from_url,
)

from deal_watcher.models import TrustedSeller, TelegramSubscriber
from deal_watcher.services import scheduler_service
from deal_watcher.services.ebay_helpers import parse_item_payload
from deal_watcher.services.trm_cache import get_trm_value_for_date
from deal_watcher.services.notifiers.telegram import send_plain_message

logger = logging.getLogger(__name__)

Resultado = SyncBajoPedidoLog.ResultadoChoices
Disponibilidad = BajoPedido.DisponibilidadEbayChoices
Estado = BajoPedido.EstadoChoices

# Sale/physical states that mean "this listing is actually backed by a real unit".
_ESTADO_PRODUCTO_CON_UNIDADES = [
    'en_stock',
    'viajando',
    'en_oficina_importadora',
    'por_comprar',
]


def _settings_decimal(name: str, default: str) -> Decimal:
    """Read a (possibly float) settings constant as a Decimal, never mixing types."""
    return Decimal(str(getattr(settings, name, default)))


def round_to(valor: Decimal, paso: Decimal) -> Decimal:
    """Round `valor` to the nearest multiple of `paso` (same rule as products.tasks)."""
    if paso <= 0:
        return valor
    return (valor / paso).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * paso


def round_up_to(valor: Decimal, paso: Decimal) -> Decimal:
    """Round `valor` UP to the next multiple of `paso`.

    Used for the margin-floor target B: rounding to the *nearest* multiple could
    land below the current price (lowering it — which breaks the "only raises"
    ratchet) or below the price that yields MARGEN_MINIMO. Ceiling guarantees the
    realized margin stays >= MARGEN_MINIMO and the ratchet never lowers the price.
    """
    if paso <= 0:
        return valor
    return (valor / paso).quantize(Decimal('1'), rounding=ROUND_CEILING) * paso


def _is_trusted(username: str) -> bool:
    """Canonical trusted-seller check, mirroring deal_checker._is_trusted."""
    if not username:
        return False
    return TrustedSeller.objects.filter(active=True, username=username).exists()


def _broadcast_telegram(text: str) -> None:
    """Send a plain HTML message to every active TelegramSubscriber.

    Reuses the low-level per-chat sender (`send_plain_message`). Fully isolated:
    a Telegram failure must never abort the sync nor flag a listing as failed.
    """
    try:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured — skipping sync alert")
            return
        for sub in TelegramSubscriber.objects.filter(active=True):
            try:
                send_plain_message(sub.chat_id, text)
            except Exception:
                logger.exception("Telegram broadcast failed for chat %s", sub.chat_id)
    except Exception:
        logger.exception("Telegram broadcast failed")


def _fmt_cop(valor) -> str:
    try:
        return f"{int(round(float(valor))):,}".replace(',', '.')
    except (TypeError, ValueError):
        return str(valor)


def sync_bajo_pedido_precios_disponibilidad() -> dict:
    """
    Run the daily eBay price & availability sync over all active eBay-linked
    `BajoPedido` listings.

    Returns a summary dict:
        {'procesados', 'subidos', 'margen_para_bajar', 'agotados', 'fallos',
         'skip_con_unidades', 'llamadas_ebay'}

    Side effects: updates `BajoPedido` rows (price/state/availability/fallos/
    timestamps), writes one `SyncBajoPedidoLog` per processed listing, sends
    Telegram alerts on price changes, and reports the eBay calls consumed to
    `scheduler_service.record_reserve_usage`.
    """
    resumen = {
        'procesados': 0,
        'subidos': 0,
        'margen_para_bajar': 0,
        'agotados': 0,
        'fallos': 0,
        'skip_con_unidades': 0,
        'llamadas_ebay': 0,
    }

    margen_minimo = _settings_decimal('MARGEN_MINIMO', '0.20')
    impuesto = _settings_decimal('IMPUESTO_IMPORTACION', '0.02')
    costo_importacion = _settings_decimal('COSTO_IMPORTACION_FIJO', '150000')
    redondeo = _settings_decimal('EBAY_PRECIO_REDONDEO_COP', '90000')
    fallos_para_agotar = int(getattr(settings, 'FALLOS_PARA_AGOTAR', 15))

    listings = (
        BajoPedido.objects.filter(active=True)
        .exclude(enlace_proveedor__isnull=True)
        .exclude(enlace_proveedor='')
        .select_related('producto')
    )

    for bp in listings.iterator():
        resumen['procesados'] += 1
        try:
            _sync_one(
                bp,
                resumen=resumen,
                margen_minimo=margen_minimo,
                impuesto=impuesto,
                costo_importacion=costo_importacion,
                redondeo=redondeo,
                fallos_para_agotar=fallos_para_agotar,
            )
        except Exception as exc:
            # A single broken listing must not abort the whole run.
            logger.exception("Unexpected error syncing BajoPedido %s", bp.pk)
            resumen['fallos'] += 1
            _safe_log(
                bp,
                resultado=Resultado.FALLO_EBAY,
                was_available=False,
                seller_is_trusted=False,
                error_message=f"unexpected: {exc}",
            )

    # Quota telemetry: report real eBay calls against the reserva once.
    if resumen['llamadas_ebay'] > 0:
        try:
            scheduler_service.record_reserve_usage(resumen['llamadas_ebay'])
        except Exception:
            logger.exception("record_reserve_usage failed (telemetry only)")

    logger.info("BajoPedido sync done: %s", resumen)
    return resumen


def _sync_one(
    bp: BajoPedido,
    *,
    resumen: dict,
    margen_minimo: Decimal,
    impuesto: Decimal,
    costo_importacion: Decimal,
    redondeo: Decimal,
    fallos_para_agotar: int,
) -> None:
    """Process a single listing. Mutates `resumen` in place."""
    # --- Backfill the legacy id on the fly when missing ---------------------
    if not bp.ebay_legacy_id:
        try:
            legacy_id = extract_legacy_id_from_url(bp.enlace_proveedor)
        except ValueError as exc:
            resumen['fallos'] += 1
            bp.ultimo_sync_at = timezone.now()
            bp.fallos_consecutivos = (bp.fallos_consecutivos or 0) + 1
            update_fields = ['ultimo_sync_at', 'fallos_consecutivos']
            # Apply the "too many failures" rule even when we never reach eBay.
            if bp.fallos_consecutivos >= fallos_para_agotar:
                bp.disponibilidad_ebay = Disponibilidad.AGOTADO
                bp.estado = Estado.SIN_EXISTENCIAS
                update_fields += ['disponibilidad_ebay', 'estado']
                resumen['agotados'] += 1
                resultado = Resultado.AGOTADO_FALLOS
            else:
                resultado = Resultado.FALLO_EBAY
            bp.save(update_fields=update_fields)
            _safe_log(
                bp,
                resultado=resultado,
                was_available=False,
                seller_is_trusted=False,
                precio_anterior=bp.precio,
                precio_nuevo=bp.precio,
                error_message=f"no_legacy_id: {exc}",
            )
            return
        bp.ebay_legacy_id = legacy_id
        bp.save(update_fields=['ebay_legacy_id'])

    # --- Frontier: never touch a listing backed by real units ---------------
    tiene_unidades = UnidadProducto.objects.filter(
        producto=bp.producto,
        condicion=bp.condicion,
        active=True,
        estado_venta='sin_vender',
        estado_producto__in=_ESTADO_PRODUCTO_CON_UNIDADES,
    ).exists()
    if tiene_unidades:
        resumen['skip_con_unidades'] += 1
        _safe_log(
            bp,
            resultado=Resultado.CON_UNIDADES_SKIP,
            was_available=False,
            seller_is_trusted=False,
            precio_anterior=bp.precio,
            precio_nuevo=bp.precio,
        )
        return

    # --- eBay lookup (counts toward the quota) ------------------------------
    resumen['llamadas_ebay'] += 1
    bp.ultimo_sync_at = timezone.now()
    try:
        payload = get_ebay_item_data(bp.ebay_legacy_id)
        snapshot = parse_item_payload(payload)
    except Exception as exc:
        _handle_lookup_failure(
            bp,
            resumen=resumen,
            fallos_para_agotar=fallos_para_agotar,
            error_message=f"ebay_lookup: {exc}",
        )
        return

    seller = snapshot.seller_username or ''
    is_trusted = _is_trusted(seller)

    # --- No usable USD price → treat as a lookup failure --------------------
    if not snapshot.has_price:
        _handle_lookup_failure(
            bp,
            resumen=resumen,
            fallos_para_agotar=fallos_para_agotar,
            error_message="no_usd_price",
            seller_username=seller,
            seller_is_trusted=is_trusted,
        )
        return

    price_usd = snapshot.price_usd

    # --- Untrusted seller → agotado immediately AND +1 fallo ----------------
    if not is_trusted:
        bp.fallos_consecutivos = (bp.fallos_consecutivos or 0) + 1
        bp.disponibilidad_ebay = Disponibilidad.AGOTADO
        bp.estado = Estado.SIN_EXISTENCIAS
        bp.ultimo_vendedor = seller
        bp.save(update_fields=[
            'fallos_consecutivos', 'disponibilidad_ebay', 'estado',
            'ultimo_vendedor', 'ultimo_sync_at',
        ])
        resumen['agotados'] += 1
        _safe_log(
            bp,
            resultado=Resultado.AGOTADO_SELLER,
            was_available=False,
            price_usd=price_usd,
            seller_username=seller,
            seller_is_trusted=False,
            precio_anterior=bp.precio,
            precio_nuevo=bp.precio,
        )
        return

    # --- Trusted but out of stock → agotado, reset fallos -------------------
    if not snapshot.is_available:
        bp.fallos_consecutivos = 0
        bp.disponibilidad_ebay = Disponibilidad.AGOTADO
        bp.estado = Estado.SIN_EXISTENCIAS
        bp.ultimo_vendedor = seller
        bp.save(update_fields=[
            'fallos_consecutivos', 'disponibilidad_ebay', 'estado',
            'ultimo_vendedor', 'ultimo_sync_at',
        ])
        resumen['agotados'] += 1
        _safe_log(
            bp,
            resultado=Resultado.SIN_CAMBIO,
            was_available=False,
            price_usd=price_usd,
            seller_username=seller,
            seller_is_trusted=True,
            precio_anterior=bp.precio,
            precio_nuevo=bp.precio,
        )
        return

    # --- Trusted + available → ratchet --------------------------------------
    try:
        trm = get_trm_value_for_date(timezone.localdate())
    except Exception as exc:
        # No TRM at all → cannot price; treat as a lookup failure.
        _handle_lookup_failure(
            bp,
            resumen=resumen,
            fallos_para_agotar=fallos_para_agotar,
            error_message=f"no_trm: {exc}",
            seller_username=seller,
            seller_is_trusted=True,
            was_available=True,
        )
        return
    if trm is None:
        _handle_lookup_failure(
            bp,
            resumen=resumen,
            fallos_para_agotar=fallos_para_agotar,
            error_message="no_trm: TRM is None",
            seller_username=seller,
            seller_is_trusted=True,
            was_available=True,
        )
        return

    trm = Decimal(str(trm))
    _apply_ratchet(
        bp,
        resumen=resumen,
        price_usd=price_usd,
        trm=trm,
        seller=seller,
        margen_minimo=margen_minimo,
        impuesto=impuesto,
        costo_importacion=costo_importacion,
        redondeo=redondeo,
    )


def _handle_lookup_failure(
    bp: BajoPedido,
    *,
    resumen: dict,
    fallos_para_agotar: int,
    error_message: str,
    seller_username: str = '',
    seller_is_trusted: bool = False,
    was_available: bool = False,
) -> None:
    """Network failure / item-not-found / no-price path.

    Keep the current state and only flip to `agotado` once we reach
    `FALLOS_PARA_AGOTAR` consecutive failures.
    """
    bp.fallos_consecutivos = (bp.fallos_consecutivos or 0) + 1
    update_fields = ['fallos_consecutivos', 'ultimo_sync_at']
    if bp.fallos_consecutivos >= fallos_para_agotar:
        bp.disponibilidad_ebay = Disponibilidad.AGOTADO
        bp.estado = Estado.SIN_EXISTENCIAS
        update_fields += ['disponibilidad_ebay', 'estado']
        resumen['agotados'] += 1
        resultado = Resultado.AGOTADO_FALLOS
    else:
        resumen['fallos'] += 1
        resultado = Resultado.FALLO_EBAY
    bp.save(update_fields=update_fields)
    _safe_log(
        bp,
        resultado=resultado,
        was_available=was_available,
        seller_username=seller_username,
        seller_is_trusted=seller_is_trusted,
        precio_anterior=bp.precio,
        precio_nuevo=bp.precio,
        error_message=error_message,
    )


def _apply_ratchet(
    bp: BajoPedido,
    *,
    resumen: dict,
    price_usd: Decimal,
    trm: Decimal,
    seller: str,
    margen_minimo: Decimal,
    impuesto: Decimal,
    costo_importacion: Decimal,
    redondeo: Decimal,
) -> None:
    """Price ratchet for a trusted, available listing.

    X = current price; Y = landed cost; B = price needed for the minimum margin.
    Raise to B when current margin is below the floor (or X<=0); never lower
    automatically — flag "margen para bajar" instead.
    """
    X = bp.precio if bp.precio is not None else Decimal('0')
    Y = (price_usd * trm) * (Decimal(1) + impuesto) + costo_importacion
    # Ceiling so the realized margin never dips below the floor and the ratchet
    # never lowers the price due to rounding (see round_up_to docstring).
    B = round_up_to(Y / (Decimal(1) - margen_minimo), redondeo)

    bp.fallos_consecutivos = 0
    bp.disponibilidad_ebay = Disponibilidad.DISPONIBLE
    bp.estado = Estado.ACTIVO
    bp.ultimo_vendedor = seller

    precio_anterior = X
    nombre = bp.producto.nombre if bp.producto else f"BajoPedido {bp.pk}"
    condicion = bp.get_condicion_display()

    # Guard X<=0 first so the margin division never raises ZeroDivisionError.
    if X <= 0 or (X - Y) / X < margen_minimo:
        bp.precio = B
        bp.save(update_fields=[
            'precio', 'fallos_consecutivos', 'disponibilidad_ebay',
            'estado', 'ultimo_vendedor', 'ultimo_sync_at',
        ])
        resumen['subidos'] += 1
        _safe_log(
            bp,
            resultado=Resultado.PRECIO_SUBIDO,
            was_available=True,
            price_usd=price_usd,
            trm_used=trm,
            seller_username=seller,
            seller_is_trusted=True,
            precio_anterior=precio_anterior,
            precio_nuevo=B,
        )
        _broadcast_telegram(
            f"🔼 Precio subido por margen — {nombre} ({condicion}): "
            f"${_fmt_cop(precio_anterior)} → ${_fmt_cop(B)} COP"
        )
        return

    # Margin is healthy; persist the (unchanged) price metadata.
    bp.save(update_fields=[
        'fallos_consecutivos', 'disponibilidad_ebay', 'estado',
        'ultimo_vendedor', 'ultimo_sync_at',
    ])

    if B < X:
        resumen['margen_para_bajar'] += 1
        _safe_log(
            bp,
            resultado=Resultado.MARGEN_PARA_BAJAR,
            was_available=True,
            price_usd=price_usd,
            trm_used=trm,
            seller_username=seller,
            seller_is_trusted=True,
            precio_anterior=precio_anterior,
            precio_nuevo=precio_anterior,
        )
        _broadcast_telegram(
            f"🔽 Margen para bajar — {nombre} ({condicion}): "
            f"podrías bajar ${_fmt_cop(X)} → ${_fmt_cop(B)} COP "
            f"(no se bajó automáticamente)"
        )
        return

    _safe_log(
        bp,
        resultado=Resultado.SIN_CAMBIO,
        was_available=True,
        price_usd=price_usd,
        trm_used=trm,
        seller_username=seller,
        seller_is_trusted=True,
        precio_anterior=precio_anterior,
        precio_nuevo=precio_anterior,
    )


def _safe_log(
    bp: BajoPedido,
    *,
    resultado: str,
    was_available: bool = False,
    price_usd: Optional[Decimal] = None,
    trm_used: Optional[Decimal] = None,
    precio_anterior: Optional[Decimal] = None,
    precio_nuevo: Optional[Decimal] = None,
    seller_username: str = '',
    seller_is_trusted: bool = False,
    error_message: str = '',
) -> None:
    """Write a SyncBajoPedidoLog row; never raise (logging must not break sync)."""
    try:
        SyncBajoPedidoLog.objects.create(
            bajo_pedido=bp,
            was_available=was_available,
            price_usd=price_usd,
            trm_used=trm_used,
            precio_anterior=precio_anterior,
            precio_nuevo=precio_nuevo,
            seller_username=(seller_username or '')[:100],
            seller_is_trusted=seller_is_trusted,
            resultado=resultado,
            error_message=error_message or '',
        )
    except Exception:
        logger.exception("Failed to write SyncBajoPedidoLog for BajoPedido %s", bp.pk)
