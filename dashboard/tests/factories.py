"""
factory_boy factories for the dashboard tests.

Notes on auto-now fields:
- `Venta.fecha`, `Separacion.fecha_separacion`, and `BaseModel.created_at` are
  `auto_now_add=True`. Django ignores user-supplied values on insert. To control
  these in tests, use the `_force_dt(model, pk, **fields)` helper which calls
  QuerySet.update() — this bypasses the field's auto behavior.
- `OrdenCompra.save()` auto-generates a `UnidadProducto` when none is provided
  AND it calls `get_trm_for_date()` (which queries the DB). To keep tests fast
  and self-contained we always pre-create the `UnidadProducto` and pass it in,
  bypassing both branches.
"""

from datetime import date, datetime, timedelta, timezone as dt_tz
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from products.models import Brand, Producto, TipoProducto, UnidadProducto
from purchases.models import OrdenCompra
from sales.models import Ciudad, Cliente, Departamento, ItemVenta, Separacion, Venta

User = get_user_model()


# ----------------------------------------------------------------------------
# Time helper — overwrite auto_now_add fields after creation.
# ----------------------------------------------------------------------------

def force_timestamp(instance, **fields):
    """
    Bypass auto_now_add by issuing a raw UPDATE on the row's pk.
    Returns the refreshed instance.
    """
    type(instance).objects.filter(pk=instance.pk).update(**fields)
    instance.refresh_from_db()
    return instance


# ----------------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------------

class AdminUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'admin{n}@test.local')
    is_staff = True
    is_superuser = True
    is_active = True


class RegularUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'user{n}@test.local')
    is_staff = False
    is_superuser = False
    is_active = True


# ----------------------------------------------------------------------------
# Geo + customer
# ----------------------------------------------------------------------------

class DepartamentoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Departamento
        django_get_or_create = ('nombre',)

    nombre = 'Antioquia'


class CiudadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ciudad
        django_get_or_create = ('nombre', 'departamento')

    nombre = 'Medellín'
    departamento = factory.SubFactory(DepartamentoFactory)


class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cliente

    nombre_completo = factory.Sequence(lambda n: f'Cliente {n}')
    cedula = factory.Sequence(lambda n: f'CED{n:08d}')
    celular = '3001234567'
    correo = factory.Sequence(lambda n: f'cliente{n}@test.local')
    direccion = 'Calle 1 # 2-3'
    ciudad = factory.SubFactory(CiudadFactory)
    departamento = factory.SubFactory(DepartamentoFactory)


# ----------------------------------------------------------------------------
# Product hierarchy
# ----------------------------------------------------------------------------

class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand
        django_get_or_create = ('name',)

    name = 'TestBrand'


class TipoProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TipoProducto
        django_get_or_create = ('nombre',)

    nombre = 'Smartphone'


class ProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Producto

    nombre = factory.Sequence(lambda n: f'Producto {n}')
    descripcion = 'Descripción de prueba'
    marca = factory.SubFactory(BrandFactory)
    tipo_producto = factory.SubFactory(TipoProductoFactory)


class UnidadProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UnidadProducto

    producto = factory.SubFactory(ProductoFactory)
    serial = factory.Sequence(lambda n: f'SERIAL-{n:06d}')
    condicion = 'nuevo'
    estado_venta = 'sin_vender'
    estado_producto = 'en_stock'
    precio = Decimal('1000000')


# ----------------------------------------------------------------------------
# Purchase order — always supply unidad_producto to skip the auto-create branch
# (which calls get_trm_for_date and creates an extra unit).
# ----------------------------------------------------------------------------

class OrdenCompraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrdenCompra

    producto = factory.SubFactory(ProductoFactory)
    unidad_producto = factory.SubFactory(
        UnidadProductoFactory,
        producto=factory.SelfAttribute('..producto'),
    )
    condicion = 'nuevo'
    estado_logistico = 'en_oficina'
    numero_orden = factory.Sequence(lambda n: f'PO-{n:05d}')
    costo_compra = Decimal('500000')
    fecha_compra = factory.LazyFunction(lambda: timezone.localdate())
    # impuesto_importacion is overwritten by save() (2% of costo_compra by default)


# ----------------------------------------------------------------------------
# Sales
# ----------------------------------------------------------------------------

class VentaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venta

    cliente = factory.SubFactory(ClienteFactory)
    estado_entrega = 'por_entregar'


class ItemVentaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ItemVenta

    venta = factory.SubFactory(VentaFactory)
    unidad_producto = factory.SubFactory(UnidadProductoFactory)
    precio = Decimal('1200000')


# ----------------------------------------------------------------------------
# Separación
# ----------------------------------------------------------------------------

class SeparacionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Separacion

    unidad_producto = factory.SubFactory(UnidadProductoFactory)
    cliente = factory.SubFactory(ClienteFactory)
    valor_abono = Decimal('100000')
    fecha_maxima_compra = factory.LazyFunction(
        lambda: timezone.localdate() + timedelta(days=30)
    )
    estado = 'activa'


# ----------------------------------------------------------------------------
# High-level helpers used across tests
# ----------------------------------------------------------------------------

def make_sold_unit(*, precio_venta, costo_compra, impuesto, fecha_venta,
                   estado_entrega='entregado', cliente=None):
    """
    Build the full chain Producto → UnidadProducto → OrdenCompra → Venta → ItemVenta
    where the sale lands on `fecha_venta` (a tz-aware datetime). Returns the venta.
    """
    producto = ProductoFactory()
    unidad = UnidadProductoFactory(producto=producto, estado_venta='vendido')
    oc = OrdenCompraFactory(
        producto=producto,
        unidad_producto=unidad,
        costo_compra=Decimal(costo_compra),
    )
    # impuesto_importacion gets overwritten by save() — patch it.
    OrdenCompra.objects.filter(pk=oc.pk).update(impuesto_importacion=Decimal(impuesto))

    venta = VentaFactory(estado_entrega=estado_entrega, cliente=cliente or ClienteFactory())
    force_timestamp(venta, fecha=fecha_venta, created_at=fecha_venta)

    ItemVentaFactory(venta=venta, unidad_producto=unidad, precio=Decimal(precio_venta))
    return venta


def make_separacion(*, dias_atras, **kw):
    """Create an active separation whose `created_at` is `dias_atras` days ago."""
    sep = SeparacionFactory(**kw)
    cutoff = timezone.now() - timedelta(days=dias_atras)
    force_timestamp(sep, created_at=cutoff)
    return sep
