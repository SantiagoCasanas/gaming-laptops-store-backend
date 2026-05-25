"""
Tests for the public catalog endpoint (Hito 6).

Covers the availability frontier resolved on the server by
`CatalogProductoSerializer` plus the public (AllowAny) access contract and the
sensitive-field allowlist.

Conventions match the rest of the products test suite: pytest + factory_boy,
`pytest.mark.django_db`, monetary assertions via Decimal. No external calls.
"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from products.models import BajoPedido, UnidadProducto
from products.tests.factories import (
    BajoPedidoFactory,
    ProductoFactory,
    UnidadProductoFactory,
)

pytestmark = pytest.mark.django_db

LIST_URL = '/products/catalogo/'


def detail_url(pk):
    return f'/products/catalogo/{pk}/'


# Fields that must NEVER leak through the public serializer.
_SENSITIVE_KEYS = {
    'serial',
    'estado_venta',
    'estado_producto',
    'enlace_proveedor',
    'ebay_legacy_id',
    'fallos_consecutivos',
    'costo',
    'costo_compra',
    'costo_importacion',
    'unidades',
    'bajo_pedidos',
    'usuario_ultima_modificacion',
    'disponibilidad_ebay',
}

# Exact allowlist the public serializer is allowed to expose.
_ALLOWED_KEYS = {
    'id', 'nombre', 'nombre_base', 'descripcion',
    'marca', 'marca_nombre',
    'tipo_producto', 'tipo_producto_nombre',
    'campo_valores', 'imagenes',
    'disponibilidad_catalogo', 'precio',
}


@pytest.fixture
def client():
    """An unauthenticated DRF client (no token) to prove AllowAny."""
    return APIClient()


def _find(rows, producto_id):
    return next((r for r in rows if r['id'] == producto_id), None)


# ---------------------------------------------------------------------------
# Frontier
# ---------------------------------------------------------------------------

def test_producto_con_unidad_disponible_es_en_stock(client):
    """Case 1: a product with an available unit → en_stock, precio=min(unidades)."""
    producto = ProductoFactory()
    UnidadProductoFactory(
        producto=producto,
        precio=Decimal('3000000'),
        estado_venta=UnidadProducto.EstadoVentaChoices.SIN_VENDER,
        estado_producto=UnidadProducto.EstadoProductoChoices.EN_STOCK,
    )
    UnidadProductoFactory(
        producto=producto,
        precio=Decimal('2500000'),
        estado_venta=UnidadProducto.EstadoVentaChoices.SIN_VENDER,
        estado_producto=UnidadProducto.EstadoProductoChoices.VIAJANDO,
    )
    # A unit that should NOT count (vendido) — must not affect price/availability.
    UnidadProductoFactory(
        producto=producto,
        precio=Decimal('100'),
        estado_venta=UnidadProducto.EstadoVentaChoices.VENDIDO,
        estado_producto=UnidadProducto.EstadoProductoChoices.ENTREGADO,
    )

    resp = client.get(LIST_URL)
    assert resp.status_code == 200

    row = _find(resp.data, producto.id)
    assert row is not None
    assert row['disponibilidad_catalogo'] == 'en_stock'
    assert Decimal(str(row['precio'])) == Decimal('2500000')


def test_unidad_disponible_tiene_prioridad_sobre_listings(client):
    """A real available unit wins even if a cheaper BajoPedido listing exists."""
    producto = ProductoFactory()
    UnidadProductoFactory(
        producto=producto,
        precio=Decimal('4000000'),
        estado_venta=UnidadProducto.EstadoVentaChoices.SIN_VENDER,
        estado_producto=UnidadProducto.EstadoProductoChoices.EN_STOCK,
    )
    BajoPedidoFactory(
        producto=producto,
        precio=Decimal('1000000'),
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
    )

    resp = client.get(detail_url(producto.id))
    assert resp.status_code == 200
    assert resp.data['disponibilidad_catalogo'] == 'en_stock'
    assert Decimal(str(resp.data['precio'])) == Decimal('4000000')


def test_sin_unidades_con_listing_disponible_es_bajo_pedido(client):
    """Case 2: no units + an available listing → bajo_pedido, precio=min(disponibles)."""
    producto = ProductoFactory()
    BajoPedidoFactory(
        producto=producto,
        condicion=BajoPedido.CondicionChoices.NUEVO,
        precio=Decimal('2200000'),
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
    )
    BajoPedidoFactory(
        producto=producto,
        condicion=BajoPedido.CondicionChoices.USADO,
        precio=Decimal('1800000'),
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
    )
    # An agotado listing must not lower the price when disponibles exist.
    BajoPedidoFactory(
        producto=producto,
        condicion=BajoPedido.CondicionChoices.OPEN_BOX,
        precio=Decimal('1'),
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.AGOTADO,
    )

    resp = client.get(LIST_URL)
    assert resp.status_code == 200
    row = _find(resp.data, producto.id)
    assert row is not None
    assert row['disponibilidad_catalogo'] == 'bajo_pedido'
    assert Decimal(str(row['precio'])) == Decimal('1800000')


def test_sin_unidades_con_listing_agotado_es_sin_existencias(client):
    """Case 3: no units + only agotado/desconocido listings → sin_existencias, last known price."""
    producto = ProductoFactory()
    BajoPedidoFactory(
        producto=producto,
        condicion=BajoPedido.CondicionChoices.NUEVO,
        precio=Decimal('2900000'),
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.AGOTADO,
    )
    BajoPedidoFactory(
        producto=producto,
        condicion=BajoPedido.CondicionChoices.USADO,
        precio=Decimal('2400000'),
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DESCONOCIDO,
    )

    resp = client.get(detail_url(producto.id))
    assert resp.status_code == 200
    assert resp.data['disponibilidad_catalogo'] == 'sin_existencias'
    # Last known price = min across all listings.
    assert Decimal(str(resp.data['precio'])) == Decimal('2400000')


def test_sin_unidades_ni_listings_no_aparece_en_lista(client):
    """Case 4: a product with neither units nor listings is excluded from the list."""
    visible = ProductoFactory()
    BajoPedidoFactory(
        producto=visible,
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
    )
    huerfano = ProductoFactory()  # no units, no listings

    resp = client.get(LIST_URL)
    assert resp.status_code == 200
    ids = {r['id'] for r in resp.data}
    assert visible.id in ids
    assert huerfano.id not in ids


def test_detalle_sin_unidades_ni_listings_no_es_404(client):
    """Detail returns the product (sin_existencias) even with no units/listings."""
    producto = ProductoFactory()
    resp = client.get(detail_url(producto.id))
    assert resp.status_code == 200
    assert resp.data['id'] == producto.id
    assert resp.data['disponibilidad_catalogo'] == 'sin_existencias'
    assert resp.data['precio'] is None


def test_producto_inactivo_da_404_en_detalle(client):
    """An inactive product is a real 404 (not exposed)."""
    producto = ProductoFactory(active=False)
    resp = client.get(detail_url(producto.id))
    assert resp.status_code == 404


def test_listing_inactivo_no_cuenta_como_disponibilidad(client):
    """An inactive BajoPedido must not make a product appear in the catalog."""
    producto = ProductoFactory()
    BajoPedidoFactory(
        producto=producto,
        active=False,
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
    )
    resp = client.get(LIST_URL)
    ids = {r['id'] for r in resp.data}
    assert producto.id not in ids


# ---------------------------------------------------------------------------
# Public access (AllowAny)
# ---------------------------------------------------------------------------

def test_acceso_anonimo_lista_200(client):
    """Case 5: anonymous client (no token) gets 200 on the list."""
    producto = ProductoFactory()
    BajoPedidoFactory(
        producto=producto,
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
    )
    resp = client.get(LIST_URL)
    assert resp.status_code == 200
    assert 'HTTP_AUTHORIZATION' not in client._credentials


def test_acceso_anonimo_detalle_200(client):
    """Anonymous client (no token) gets 200 on the detail."""
    producto = ProductoFactory()
    UnidadProductoFactory(producto=producto)
    resp = client.get(detail_url(producto.id))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Performance — no N+1
# ---------------------------------------------------------------------------

def test_lista_no_tiene_n_mas_1(client, django_assert_max_num_queries):
    """Query count stays flat regardless of how many products are listed."""
    for _ in range(5):
        p = ProductoFactory()
        UnidadProductoFactory(producto=p)
        BajoPedidoFactory(
            producto=p,
            disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
        )

    # select_related (marca, tipo_producto) folds into the base query; the four
    # prefetches add a fixed number of queries that does NOT grow with rows.
    with django_assert_max_num_queries(8):
        resp = client.get(LIST_URL)
    assert resp.status_code == 200
    assert len(resp.data) == 5


# ---------------------------------------------------------------------------
# Security — allowlist / no sensitive leakage
# ---------------------------------------------------------------------------

def test_respuesta_no_filtra_campos_sensibles(client):
    """Case 6: the payload never contains sensitive keys; only the allowlist."""
    producto = ProductoFactory()
    UnidadProductoFactory(
        producto=producto,
        serial='SECRET-SERIAL-123',
        estado_venta=UnidadProducto.EstadoVentaChoices.SIN_VENDER,
        estado_producto=UnidadProducto.EstadoProductoChoices.EN_STOCK,
    )
    BajoPedidoFactory(
        producto=producto,
        enlace_proveedor='https://www.ebay.com/itm/999999999999',
        ebay_legacy_id='999999999999',
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
    )

    # List
    list_resp = client.get(LIST_URL)
    row = _find(list_resp.data, producto.id)
    assert row is not None
    assert set(row.keys()) == _ALLOWED_KEYS
    assert _SENSITIVE_KEYS.isdisjoint(row.keys())

    # Detail
    detail_resp = client.get(detail_url(producto.id))
    assert set(detail_resp.data.keys()) == _ALLOWED_KEYS
    assert _SENSITIVE_KEYS.isdisjoint(detail_resp.data.keys())

    # Defensive: serialized text must not contain the secret serial.
    assert 'SECRET-SERIAL-123' not in str(detail_resp.data)
    assert 'ebay.com/itm' not in str(detail_resp.data)
