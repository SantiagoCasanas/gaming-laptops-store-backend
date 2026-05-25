"""
Celery tasks for automated price updates for BajoPedido (on-demand sourcing) via eBay API.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.conf import settings
from celery import shared_task

from core.services.trm_service import get_trm_for_date
from products.models import BajoPedido
from products.services.ebay_service import (
    get_ebay_item_data,
    extract_legacy_id_from_url,
)

logger = logging.getLogger(__name__)


@shared_task(name='products.tasks.actualizar_precios_bajo_pedido', bind=True, max_retries=3)
def actualizar_precios_bajo_pedido(self):
    """
    DEPRECATED (Hito 4): superseded by products.services.bajo_pedido_sync_service.sync_bajo_pedido_precios_disponibilidad; no longer invoked by correr_tareas_programadas. Kept for rollback.

    Daily task: Fetch prices from eBay for all BajoPedido records with enlace_proveedor.
    Updates BajoPedido.precio and BajoPedido.estado based on availability.

    Only processes BajoPedido records that:
    - Are active (active=True)
    - Have an eBay link (enlace_proveedor is not null/empty)
    - Have proveedor = 'eBay' (if proveedor is specified)

    State updates:
    - If no stock found on eBay → estado = 'sin_existencias'
    - If stock found → estado = 'activo'

    Price formula: ((precio_usd * 1.2) + 50) * TRM, rounded to nearest 90,000 COP

    Retries up to 3 times on failure with exponential backoff.
    """
    bajo_pedidos_actualizado = 0
    bajo_pedidos_error = 0
    bajo_pedidos_salto = 0

    try:
        # Fetch all active BajoPedido records with eBay links
        bajo_pedidos = BajoPedido.objects.filter(
            active=True,
            enlace_proveedor__isnull=False,
        ).exclude(
            enlace_proveedor=''
        ).select_related('producto', 'proveedor')

        logger.info(f"Starting BajoPedido price update task. Found {bajo_pedidos.count()} records.")

        for bajo_pedido in bajo_pedidos:
            try:
                # Skip non-eBay suppliers
                if bajo_pedido.proveedor and bajo_pedido.proveedor.slug != 'ebay':
                    logger.debug(f"Skipping BajoPedido {bajo_pedido.id}: proveedor is {bajo_pedido.proveedor.slug}, not eBay")
                    bajo_pedidos_salto += 1
                    continue

                # Extract legacy ID from eBay URL
                if not bajo_pedido.enlace_proveedor:
                    logger.warning(f"BajoPedido {bajo_pedido.id} has no enlace_proveedor, skipping")
                    bajo_pedidos_salto += 1
                    continue

                try:
                    legacy_id = extract_legacy_id_from_url(bajo_pedido.enlace_proveedor)
                except ValueError as e:
                    logger.error(f"BajoPedido {bajo_pedido.id}: {str(e)}")
                    bajo_pedidos_error += 1
                    continue

                # Fetch item data from eBay
                try:
                    item_data = get_ebay_item_data(legacy_id)
                except Exception as e:
                    logger.error(f"BajoPedido {bajo_pedido.id} (legacy ID {legacy_id}): {str(e)}")
                    bajo_pedidos_error += 1
                    continue

                # Extract price (primary price or current bid)
                price_summary = item_data.get('price')
                if not price_summary:
                    logger.error(f"BajoPedido {bajo_pedido.id}: No price data in eBay response")
                    bajo_pedidos_error += 1
                    continue

                precio_proveedor_usd = Decimal(str(price_summary.get('value', 0)))
                if precio_proveedor_usd <= 0:
                    logger.warning(f"BajoPedido {bajo_pedido.id}: Invalid price {precio_proveedor_usd}, marking as sin_existencias")
                    bajo_pedido.estado = BajoPedido.EstadoChoices.SIN_EXISTENCIAS
                    bajo_pedido.save(update_fields=['estado'])
                    bajo_pedidos_error += 1
                    continue

                # Get availability status from eBay
                availability_status = item_data.get('estimatedAvailabilities', [{}])[0].get('availabilityStatus', '')
                tiene_stock = availability_status.lower() in ['available_for_purchase', 'available']

                # Get TRM for today
                try:
                    trm_record = get_trm_for_date(timezone.localdate())
                    trm_usada = trm_record.valor_cop
                except ValueError as e:
                    logger.error(f"BajoPedido {bajo_pedido.id}: {str(e)}")
                    bajo_pedidos_error += 1
                    continue

                # Calculate selling price using formula: ((costo_usd * 1.2) + 50) * TRM
                precio_venta_usd = (
                    precio_proveedor_usd * Decimal('1.2')
                ) + Decimal('50')

                precio_venta_cop_raw = precio_venta_usd * trm_usada

                # Round to nearest EBAY_PRECIO_REDONDEO_COP (default 90,000)
                REDONDEO = Decimal(str(settings.EBAY_PRECIO_REDONDEO_COP if hasattr(settings, 'EBAY_PRECIO_REDONDEO_COP') else '90000'))
                precio_venta_cop = (
                    (precio_venta_cop_raw / REDONDEO).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * REDONDEO
                )

                # Update BajoPedido with new price and availability state
                nuevo_estado = BajoPedido.EstadoChoices.ACTIVO if tiene_stock else BajoPedido.EstadoChoices.SIN_EXISTENCIAS

                bajo_pedido.precio = precio_venta_cop
                bajo_pedido.estado = nuevo_estado
                bajo_pedido.save(update_fields=['precio', 'estado'])

                logger.info(
                    f"BajoPedido {bajo_pedido.id} ({bajo_pedido.producto.nombre}, {bajo_pedido.condicion}): "
                    f"Price updated to {precio_venta_cop} COP, estado={nuevo_estado}"
                )
                bajo_pedidos_actualizado += 1

            except Exception as e:
                logger.exception(f"Unexpected error processing BajoPedido {bajo_pedido.id}: {str(e)}")
                bajo_pedidos_error += 1
                continue

        logger.info(
            f"BajoPedido price update task completed. "
            f"Updated: {bajo_pedidos_actualizado}, Errors: {bajo_pedidos_error}, Skipped: {bajo_pedidos_salto}"
        )

        return {
            'status': 'success',
            'actualizado': bajo_pedidos_actualizado,
            'errores': bajo_pedidos_error,
            'salto': bajo_pedidos_salto,
        }

    except Exception as e:
        logger.exception(f"Fatal error in BajoPedido price update task: {str(e)}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error("Max retries reached, giving up on price update task")
            return {
                'status': 'failed',
                'error': str(e),
            }
