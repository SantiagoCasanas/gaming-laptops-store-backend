from rest_framework import serializers
from django.db import transaction
from .models import Invoice, Cliente, SolicitudBajoPedido, Separacion, Venta, ItemVenta, Departamento, Ciudad
from products.models import UnidadProducto


# ---------------------------------------------------------------------------
# Cliente Serializers
# ---------------------------------------------------------------------------

class ClienteSerializer(serializers.ModelSerializer):
    """
    Serializer for Cliente model.
    Used for listing and retrieving customer information.
    """
    ciudad_nombre = serializers.CharField(source='ciudad.nombre', read_only=True)
    departamento_nombre = serializers.CharField(source='departamento.nombre', read_only=True)

    class Meta:
        model = Cliente
        fields = ['id', 'nombre_completo', 'cedula', 'celular', 'correo', 'direccion', 'ciudad', 'ciudad_nombre', 'departamento', 'departamento_nombre', 'active']


class ClienteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new customer.
    """
    class Meta:
        model = Cliente
        fields = ['nombre_completo', 'cedula', 'celular', 'correo', 'direccion', 'ciudad', 'departamento']

    def create(self, validated_data):
        """Create and return a new customer instance."""
        cliente = Cliente.objects.create(**validated_data)
        return cliente


class ClienteUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating customer information.
    """
    class Meta:
        model = Cliente
        fields = ['nombre_completo', 'cedula', 'celular', 'correo', 'direccion', 'ciudad', 'departamento']

    def update(self, instance, validated_data):
        """Update and return the customer instance."""
        instance.nombre_completo = validated_data.get('nombre_completo', instance.nombre_completo)
        instance.cedula = validated_data.get('cedula', instance.cedula)
        instance.celular = validated_data.get('celular', instance.celular)
        instance.correo = validated_data.get('correo', instance.correo)
        instance.direccion = validated_data.get('direccion', instance.direccion)
        instance.ciudad = validated_data.get('ciudad', instance.ciudad)
        instance.departamento = validated_data.get('departamento', instance.departamento)
        instance.save()
        return instance


# ---------------------------------------------------------------------------
# SolicitudBajoPedido Serializers
# ---------------------------------------------------------------------------

class SolicitudBajoPedidoSerializer(serializers.ModelSerializer):
    """
    Serializer for SolicitudBajoPedido model.
    Used for listing and retrieving back order information.
    """
    bajo_pedido_str = serializers.CharField(source='bajo_pedido.__str__', read_only=True)
    bajo_pedido_producto_id = serializers.IntegerField(source='bajo_pedido.producto.id', read_only=True)
    bajo_pedido_producto_nombre = serializers.CharField(source='bajo_pedido.producto.nombre', read_only=True)
    bajo_pedido_condicion = serializers.CharField(source='bajo_pedido.condicion', read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre_completo', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    orden_compra_estado = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudBajoPedido
        fields = [
            'id', 'bajo_pedido', 'bajo_pedido_str', 'bajo_pedido_producto_id',
            'bajo_pedido_producto_nombre', 'bajo_pedido_condicion',
            'cliente', 'cliente_nombre',
            'valor_abono', 'fecha_solicitud', 'fecha_maxima_compra', 'orden_compra',
            'orden_compra_estado', 'estado', 'estado_display', 'active'
        ]

    def get_orden_compra_estado(self, obj):
        if obj.orden_compra:
            return obj.orden_compra.estado_logistico
        return None


class SolicitudBajoPedidoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new back order.
    """
    class Meta:
        model = SolicitudBajoPedido
        fields = [
            'bajo_pedido', 'cliente', 'valor_abono', 'fecha_maxima_compra'
        ]

    def create(self, validated_data):
        """Create and return a new back order instance."""
        sbp = SolicitudBajoPedido.objects.create(**validated_data)
        return sbp


class SolicitudBajoPedidoUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating back order information.
    """
    class Meta:
        model = SolicitudBajoPedido
        fields = [
            'valor_abono', 'fecha_maxima_compra', 'estado', 'orden_compra'
        ]

    def update(self, instance, validated_data):
        """Update and return the back order instance."""
        instance.valor_abono = validated_data.get('valor_abono', instance.valor_abono)
        instance.fecha_maxima_compra = validated_data.get('fecha_maxima_compra', instance.fecha_maxima_compra)
        instance.estado = validated_data.get('estado', instance.estado)
        instance.orden_compra = validated_data.get('orden_compra', instance.orden_compra)
        instance.save()
        return instance


# ---------------------------------------------------------------------------
# Separacion Serializers
# ---------------------------------------------------------------------------

class SeparacionSerializer(serializers.ModelSerializer):
    """
    Serializer for Separacion model.
    Used for listing and retrieving hold/separation information.
    """
    unidad_serial = serializers.CharField(source='unidad_producto.serial', read_only=True)
    unidad_estado_venta = serializers.CharField(source='unidad_producto.estado_venta', read_only=True)
    unidad_estado_producto = serializers.CharField(source='unidad_producto.estado_producto', read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre_completo', read_only=True)
    producto_nombre = serializers.CharField(source='unidad_producto.producto.nombre', read_only=True)
    unidad_precio = serializers.DecimalField(source='unidad_producto.precio', max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Separacion
        fields = [
            'id', 'unidad_producto', 'unidad_serial', 'unidad_estado_venta', 'unidad_estado_producto',
            'producto_nombre', 'unidad_precio',
            'cliente', 'cliente_nombre',
            'valor_abono', 'fecha_separacion', 'fecha_maxima_compra', 'estado', 'active'
        ]


class SeparacionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new hold/separation.
    """
    class Meta:
        model = Separacion
        fields = [
            'unidad_producto', 'cliente', 'valor_abono', 'fecha_maxima_compra'
        ]

    def create(self, validated_data):
        """Create hold and mark unit as 'separado'."""
        sep = Separacion.objects.create(**validated_data)
        unidad = sep.unidad_producto
        unidad.estado_venta = 'separado'
        unidad.save(update_fields=['estado_venta'])
        return sep


class SeparacionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating hold/separation information.
    """
    class Meta:
        model = Separacion
        fields = [
            'valor_abono', 'fecha_maxima_compra', 'estado'
        ]

    def update(self, instance, validated_data):
        """Update and return the hold instance."""
        old_estado = instance.estado
        instance.valor_abono = validated_data.get('valor_abono', instance.valor_abono)
        instance.fecha_maxima_compra = validated_data.get('fecha_maxima_compra', instance.fecha_maxima_compra)
        instance.estado = validated_data.get('estado', instance.estado)
        instance.save()

        # When canceled, restore unit to sin_vender
        if old_estado != 'cancelada' and instance.estado == 'cancelada':
            unidad = instance.unidad_producto
            unidad.estado_venta = 'sin_vender'
            unidad.save(update_fields=['estado_venta'])

        return instance


# ---------------------------------------------------------------------------
# Departamento & Ciudad Serializers
# ---------------------------------------------------------------------------

class DepartamentoSerializer(serializers.ModelSerializer):
    """Serializer for Departamento model."""
    class Meta:
        model = Departamento
        fields = ['id', 'nombre', 'codigo', 'active']


class CiudadSerializer(serializers.ModelSerializer):
    """Serializer for Ciudad model with department info."""
    departamento_nombre = serializers.CharField(source='departamento.nombre', read_only=True)

    class Meta:
        model = Ciudad
        fields = ['id', 'nombre', 'departamento', 'departamento_nombre', 'active']


class CiudadByCiudadDepartamentoSerializer(serializers.ModelSerializer):
    """Serializer for Ciudad, nested under Departamento."""
    class Meta:
        model = Ciudad
        fields = ['id', 'nombre', 'active']


# ---------------------------------------------------------------------------
# Venta, ItemVenta Serializers
# ---------------------------------------------------------------------------

class ItemVentaSerializer(serializers.ModelSerializer):
    """Serializer for ItemVenta model."""
    unidad_serial = serializers.CharField(source='unidad_producto.serial', read_only=True)
    producto_nombre = serializers.CharField(source='unidad_producto.variante.producto.nombre', read_only=True)
    unidad_estado_producto = serializers.CharField(source='unidad_producto.estado_producto', read_only=True)
    unidad_estado_venta = serializers.CharField(source='unidad_producto.estado_venta', read_only=True)

    class Meta:
        model = ItemVenta
        fields = [
            'id', 'venta', 'unidad_producto', 'unidad_serial', 'producto_nombre',
            'unidad_estado_producto', 'unidad_estado_venta',
            'precio', 'active',
        ]


class ItemVentaCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ItemVenta."""
    class Meta:
        model = ItemVenta
        fields = ['unidad_producto', 'precio']

    def create(self, validated_data):
        """Create ItemVenta."""
        return ItemVenta.objects.create(**validated_data)


class VentaSerializer(serializers.ModelSerializer):
    """Serializer for Venta model."""
    cliente_nombre = serializers.CharField(source='cliente.nombre_completo', read_only=True)
    items = ItemVentaSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = ['id', 'cliente', 'cliente_nombre', 'fecha', 'notas', 'separacion', 'items', 'total', 'estado_entrega', 'active']

    def get_total(self, obj):
        """Calculate total sale amount."""
        return sum(item.precio for item in obj.items.all())


class VentaCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Venta."""
    items_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        help_text="List of items to add: [{'unidad_producto': id, 'precio': amount}, ...]"
    )

    class Meta:
        model = Venta
        fields = ['cliente', 'notas', 'separacion', 'items_data', 'estado_entrega']

    @transaction.atomic
    def create(self, validated_data):
        """Create Venta with associated ItemVenta records and mark units as 'vendido'."""
        items_data = validated_data.pop('items_data')
        venta = Venta.objects.create(**validated_data)

        for item_data in items_data:
            unidad = UnidadProducto.objects.get(pk=int(item_data['unidad_producto']))
            precio = item_data['precio']
            ItemVenta.objects.create(venta=venta, unidad_producto=unidad, precio=precio)
            unidad.estado_venta = 'vendido'
            unidad.precio = precio
            unidad.save(update_fields=['estado_venta', 'precio'])

        return venta


class VentaUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Venta — cliente, notas, and estado_entrega are editable."""
    class Meta:
        model = Venta
        fields = ['cliente', 'notas', 'estado_entrega']

    def update(self, instance, validated_data):
        old_estado = instance.estado_entrega
        instance.cliente = validated_data.get('cliente', instance.cliente)
        instance.notas = validated_data.get('notas', instance.notas)
        instance.estado_entrega = validated_data.get('estado_entrega', instance.estado_entrega)
        instance.save()

        # Cascade to units when sale is marked as delivered
        if old_estado != 'entregado' and instance.estado_entrega == 'entregado':
            for item in instance.items.select_related('unidad_producto').all():
                item.unidad_producto.estado_producto = 'entregado'
                item.unidad_producto.save(update_fields=['estado_producto'])

        return instance


# ---------------------------------------------------------------------------
# Invoice Serializers
# ---------------------------------------------------------------------------

class InvoiceSerializer(serializers.ModelSerializer):
    bill_id = serializers.CharField(read_only=True)
    file_path = serializers.CharField(read_only=True, allow_null=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre_completo', read_only=True)
    cliente_cedula = serializers.CharField(source='cliente.cedula', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'bill_id',
            'cliente',
            'cliente_nombre',
            'cliente_cedula',
            'venta',
            'separacion',
            'concepto',
            'item',
            'serial_item',
            'total_amount',
            'payment_method',
            'due_date',
            'file_path',
            'email_sent',
            'active',
        ]
        read_only_fields = ['id', 'bill_id', 'file_path', 'email_sent', 'active']

    def validate(self, attrs):
        # Validate that venta and separacion are not both provided
        if attrs.get('venta') and attrs.get('separacion'):
            raise serializers.ValidationError(
                "An invoice cannot be linked to both a venta and a separacion."
            )
        # Required fields validation
        required_fields = ['cliente', 'concepto', 'serial_item', 'total_amount', 'payment_method', 'due_date']
        errors = {}
        for field in required_fields:
            value = attrs.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors[field] = 'Este campo es requerido.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class InvoiceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updates — bill_id is never changed after creation."""

    class Meta:
        model = Invoice
        fields = [
            'cliente',
            'venta',
            'separacion',
            'concepto',
            'item',
            'serial_item',
            'total_amount',
            'payment_method',
            'due_date',
        ]
