"""
Tests for the read-only Bajo Pedido sync-log API (Hito 7).

Covers the admin/monitoring endpoint that surfaces the daily eBay sync audit
log plus the per-listing sync state added to the admin BajoPedido serializers.

Conventions match the rest of the products test suite: pytest + factory_boy,
`pytest.mark.django_db`, APIClient. No external calls.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from products.models import BajoPedido, SyncBajoPedidoLog
from products.tests.factories import (
    BajoPedidoFactory,
    SyncBajoPedidoLogFactory,
)
from users.models import User

pytestmark = pytest.mark.django_db

LOGS_URL = '/products/sync-bajo-pedido/logs/'


@pytest.fixture
def user():
    return User.objects.create_user(email='admin@x.com', password='pw')


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_client():
    return APIClient()


def _rows(resp):
    """The endpoint returns a plain JSON array (no pagination wrapper)."""
    return resp.data


# ---------------------------------------------------------------------------
# Auth (IsAuthenticated)
# ---------------------------------------------------------------------------

def test_anonimo_no_puede_listar_logs(anon_client):
    resp = anon_client.get(LOGS_URL)
    assert resp.status_code in (401, 403)


def test_autenticado_listar_logs_200(auth_client):
    SyncBajoPedidoLogFactory()
    resp = auth_client.get(LOGS_URL)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Shape + ordering
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = {
    'id', 'bajo_pedido', 'producto_nombre',
    'condicion', 'condicion_display',
    'resultado', 'resultado_display',
    'was_available', 'price_usd', 'trm_used',
    'precio_anterior', 'precio_nuevo',
    'seller_username', 'seller_is_trusted',
    'error_message', 'checked_at',
}


def test_log_expone_los_campos_esperados(auth_client):
    bp = BajoPedidoFactory(condicion=BajoPedido.CondicionChoices.OPEN_BOX)
    SyncBajoPedidoLogFactory(
        bajo_pedido=bp,
        resultado=SyncBajoPedidoLog.ResultadoChoices.PRECIO_SUBIDO,
        seller_username='antonline',
    )

    resp = auth_client.get(LOGS_URL)
    assert resp.status_code == 200
    row = _rows(resp)[0]

    assert set(row.keys()) == _EXPECTED_KEYS
    assert row['producto_nombre'] == bp.producto.nombre
    assert row['condicion'] == 'open_box'
    assert row['condicion_display'] == 'Open Box'
    assert row['resultado'] == 'precio_subido'
    assert row['resultado_display'] == 'Price Raised'
    assert row['seller_username'] == 'antonline'


def test_logs_ordenados_por_checked_at_desc(auth_client):
    # Three logs; force distinct checked_at (auto_now_add can't be set on create).
    now = timezone.now()
    l_old = SyncBajoPedidoLogFactory()
    l_mid = SyncBajoPedidoLogFactory()
    l_new = SyncBajoPedidoLogFactory()
    SyncBajoPedidoLog.objects.filter(pk=l_old.pk).update(
        checked_at=now - timezone.timedelta(days=3))
    SyncBajoPedidoLog.objects.filter(pk=l_mid.pk).update(
        checked_at=now - timezone.timedelta(days=1))
    SyncBajoPedidoLog.objects.filter(pk=l_new.pk).update(checked_at=now)

    resp = auth_client.get(LOGS_URL)
    ids = [r['id'] for r in _rows(resp)]
    assert ids == [l_new.pk, l_mid.pk, l_old.pk]


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def test_filtro_por_bajo_pedido(auth_client):
    bp_a = BajoPedidoFactory()
    bp_b = BajoPedidoFactory()
    SyncBajoPedidoLogFactory.create_batch(2, bajo_pedido=bp_a)
    SyncBajoPedidoLogFactory(bajo_pedido=bp_b)

    resp = auth_client.get(LOGS_URL, {'bajo_pedido': bp_a.id})
    rows = _rows(resp)
    assert len(rows) == 2
    assert all(r['bajo_pedido'] == bp_a.id for r in rows)


def test_filtro_por_resultado(auth_client):
    SyncBajoPedidoLogFactory(
        resultado=SyncBajoPedidoLog.ResultadoChoices.FALLO_EBAY,
        error_message='timeout',
    )
    SyncBajoPedidoLogFactory(
        resultado=SyncBajoPedidoLog.ResultadoChoices.SIN_CAMBIO,
    )

    resp = auth_client.get(LOGS_URL, {'resultado': 'fallo_ebay'})
    rows = _rows(resp)
    assert len(rows) == 1
    assert rows[0]['resultado'] == 'fallo_ebay'
    assert rows[0]['error_message'] == 'timeout'


# ---------------------------------------------------------------------------
# Time window (?dias=)
# ---------------------------------------------------------------------------

def test_ventana_dias_acota_por_defecto_30(auth_client):
    """Default window keeps recent rows and drops rows older than 30 days."""
    now = timezone.now()
    reciente = SyncBajoPedidoLogFactory()
    viejo = SyncBajoPedidoLogFactory()
    SyncBajoPedidoLog.objects.filter(pk=reciente.pk).update(
        checked_at=now - timezone.timedelta(days=5))
    SyncBajoPedidoLog.objects.filter(pk=viejo.pk).update(
        checked_at=now - timezone.timedelta(days=60))

    resp = auth_client.get(LOGS_URL)  # no ?dias → default 30
    ids = {r['id'] for r in _rows(resp)}
    assert reciente.pk in ids
    assert viejo.pk not in ids


def test_ventana_dias_personalizada(auth_client):
    """?dias=2 narrows the window further."""
    now = timezone.now()
    dentro = SyncBajoPedidoLogFactory()
    fuera = SyncBajoPedidoLogFactory()
    SyncBajoPedidoLog.objects.filter(pk=dentro.pk).update(
        checked_at=now - timezone.timedelta(days=1))
    SyncBajoPedidoLog.objects.filter(pk=fuera.pk).update(
        checked_at=now - timezone.timedelta(days=10))

    resp = auth_client.get(LOGS_URL, {'dias': 2})
    ids = {r['id'] for r in _rows(resp)}
    assert dentro.pk in ids
    assert fuera.pk not in ids


def test_ventana_dias_cero_desactiva_el_filtro(auth_client):
    """?dias=0 returns even very old rows (window disabled)."""
    now = timezone.now()
    viejo = SyncBajoPedidoLogFactory()
    SyncBajoPedidoLog.objects.filter(pk=viejo.pk).update(
        checked_at=now - timezone.timedelta(days=400))

    resp = auth_client.get(LOGS_URL, {'dias': 0})
    ids = {r['id'] for r in _rows(resp)}
    assert viejo.pk in ids


# ---------------------------------------------------------------------------
# BajoPedido admin serializers now carry the sync state (7.2)
# ---------------------------------------------------------------------------

def test_bajo_pedido_list_incluye_estado_sync(auth_client):
    bp = BajoPedidoFactory(
        ebay_legacy_id='999888777',
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.DISPONIBLE,
        fallos_consecutivos=2,
        ultimo_vendedor='antonline',
    )
    bp.ultimo_sync_at = timezone.now()
    bp.save(update_fields=['ultimo_sync_at'])

    resp = auth_client.get('/products/variantes/list/')
    assert resp.status_code == 200
    row = next(r for r in resp.data if r['id'] == bp.id)

    # Pre-existing fields must still be present (only ADD).
    assert 'precio' in row and 'condicion_display' in row and 'estado_display' in row
    # New sync-state fields.
    assert row['ebay_legacy_id'] == '999888777'
    assert row['disponibilidad_ebay'] == 'disponible'
    assert row['disponibilidad_ebay_display'] == 'Available'
    assert row['fallos_consecutivos'] == 2
    assert row['ultimo_vendedor'] == 'antonline'
    assert row['ultimo_sync_at'] is not None


def test_bajo_pedido_detail_incluye_estado_sync(auth_client):
    bp = BajoPedidoFactory(
        disponibilidad_ebay=BajoPedido.DisponibilidadEbayChoices.AGOTADO,
    )
    resp = auth_client.get(f'/products/variantes/{bp.id}/detail/')
    assert resp.status_code == 200
    assert resp.data['disponibilidad_ebay'] == 'agotado'
    assert resp.data['disponibilidad_ebay_display'] == 'Sold Out'
    assert 'fallos_consecutivos' in resp.data
    assert 'ultimo_sync_at' in resp.data
    assert 'ultimo_vendedor' in resp.data
