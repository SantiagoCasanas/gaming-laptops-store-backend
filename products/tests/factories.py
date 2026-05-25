"""
factory_boy factories for the products test suite.

Minimal valid fixtures for the Bajo Pedido daily sync tests (Hito 5). Only the
FK-mandatory chain is built: Brand → TipoProducto → Producto, plus BajoPedido /
UnidadProducto factories.
"""
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from products.models import (
    BajoPedido,
    Brand,
    Producto,
    SyncBajoPedidoLog,
    TipoProducto,
    UnidadProducto,
)


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = Brand
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Brand {n}')


class TipoProductoFactory(DjangoModelFactory):
    class Meta:
        model = TipoProducto
        django_get_or_create = ('nombre',)

    nombre = factory.Sequence(lambda n: f'Tipo {n}')


class ProductoFactory(DjangoModelFactory):
    class Meta:
        model = Producto

    nombre = factory.Sequence(lambda n: f'Producto {n}')
    descripcion = 'Descripción de prueba'
    marca = factory.SubFactory(BrandFactory)
    tipo_producto = factory.SubFactory(TipoProductoFactory)


class BajoPedidoFactory(DjangoModelFactory):
    """An eBay-linked listing ready to be synced.

    `ebay_legacy_id` is pre-filled so `_sync_one` skips the URL-parsing backfill
    branch and goes straight to the eBay lookup, keeping tests focused.
    """
    class Meta:
        model = BajoPedido

    producto = factory.SubFactory(ProductoFactory)
    condicion = BajoPedido.CondicionChoices.NUEVO
    precio = Decimal('2000000')
    enlace_proveedor = factory.Sequence(
        lambda n: f'https://www.ebay.com/itm/12345600{n:05d}'
    )
    ebay_legacy_id = factory.Sequence(lambda n: f'12345600{n:05d}')
    estado = BajoPedido.EstadoChoices.ACTIVO
    disponibilidad_ebay = BajoPedido.DisponibilidadEbayChoices.DESCONOCIDO
    fallos_consecutivos = 0


class UnidadProductoFactory(DjangoModelFactory):
    class Meta:
        model = UnidadProducto

    producto = factory.SubFactory(ProductoFactory)
    serial = factory.Sequence(lambda n: f'SERIAL-{n:06d}')
    condicion = UnidadProducto.CondicionChoices.NUEVO
    estado_venta = UnidadProducto.EstadoVentaChoices.SIN_VENDER
    estado_producto = UnidadProducto.EstadoProductoChoices.EN_STOCK
    precio = Decimal('2000000')


class SyncBajoPedidoLogFactory(DjangoModelFactory):
    """A single daily-sync audit row for a listing (Hito 7).

    `checked_at` is auto_now_add, so it can't be set at create time; tests that
    need a specific timestamp must update it with `queryset.update(...)` after
    creation.
    """
    class Meta:
        model = SyncBajoPedidoLog

    bajo_pedido = factory.SubFactory(BajoPedidoFactory)
    was_available = True
    price_usd = Decimal('1500.00')
    trm_used = Decimal('4000.00')
    precio_anterior = Decimal('6000000')
    precio_nuevo = Decimal('6100000')
    seller_username = factory.Sequence(lambda n: f'seller{n}')
    seller_is_trusted = True
    resultado = SyncBajoPedidoLog.ResultadoChoices.SIN_CAMBIO
    error_message = ''
