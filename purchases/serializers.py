from rest_framework import serializers
from django.db import transaction
from .models import OrdenCompra
from products.models import UnidadProducto, Proveedor, BajoPedido, Producto
from sales.models import Cliente, SolicitudBajoPedido


class OrdenCompraSerializer(serializers.ModelSerializer):
    """
    Serializer for OrdenCompra model.
    Used for listing and retrieving purchase order information.
    """
    unidad_serial = serializers.CharField(source='unidad_producto.serial', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    condicion_display = serializers.CharField(source='get_condicion_display', read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True, allow_null=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre_completo', read_only=True, allow_null=True)
    impuesto_importacion = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrdenCompra
        fields = [
            'id', 'producto', 'producto_nombre', 'condicion', 'condicion_display',
            'unidad_producto', 'unidad_serial', 'tipo', 'estado_logistico',
            'proveedor', 'proveedor_nombre', 'cliente', 'cliente_nombre',
            'numero_orden', 'numero_tracking', 'costo_compra', 'precio_venta',
            'costo_importacion', 'impuesto_importacion', 'active'
        ]


class OrdenCompraCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new purchase order.
    Automatically creates a UnidadProducto when the order is created.
    """
    class Meta:
        model = OrdenCompra
        fields = [
            'producto', 'condicion', 'tipo', 'proveedor', 'cliente', 'numero_orden',
            'numero_tracking', 'costo_compra', 'precio_venta', 'costo_importacion', 'estado_logistico'
        ]

    def validate(self, attrs):
        """Ensure tipo-specific fields are provided."""
        tipo = attrs.get('tipo')

        if tipo == OrdenCompra.TipoChoices.COMPRA_EXTERNA:
            if not attrs.get('proveedor'):
                raise serializers.ValidationError(
                    "External purchases require 'proveedor'"
                )
        elif tipo == OrdenCompra.TipoChoices.CANJE_CLIENTE:
            if not attrs.get('cliente'):
                raise serializers.ValidationError(
                    "Trade-in purchases require 'cliente'"
                )

        return attrs

    def create(self, validated_data):
        """Create purchase order. UnidadProducto is auto-created via OrdenCompra.save()."""
        orden = OrdenCompra.objects.create(
            usuario_ultima_modificacion=self.context.get('request').user if self.context.get('request') else None,
            **validated_data
        )
        return orden


class OrdenCompraUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating purchase order information.
    impuesto_importacion is read-only (auto-calculated).
    """
    impuesto_importacion = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrdenCompra
        fields = [
            'tipo', 'proveedor', 'cliente', 'numero_orden',
            'numero_tracking', 'costo_compra', 'costo_importacion', 'impuesto_importacion',
            'estado_logistico'
        ]

    def validate(self, attrs):
        """Ensure tipo-specific fields are provided."""
        instance = self.instance
        tipo = attrs.get('tipo', instance.tipo)

        if tipo == OrdenCompra.TipoChoices.COMPRA_EXTERNA:
            proveedor = attrs.get('proveedor', instance.proveedor)
            numero_orden = attrs.get('numero_orden', instance.numero_orden)
            if not proveedor or not numero_orden:
                raise serializers.ValidationError(
                    "External purchases require 'proveedor' and 'numero_orden'"
                )
        elif tipo == OrdenCompra.TipoChoices.CANJE_CLIENTE:
            cliente = attrs.get('cliente', instance.cliente)
            if not cliente:
                raise serializers.ValidationError(
                    "Trade-in purchases require 'cliente'"
                )

        return attrs

    def update(self, instance, validated_data):
        """Update and return the purchase order instance."""
        instance.tipo = validated_data.get('tipo', instance.tipo)
        instance.proveedor = validated_data.get('proveedor', instance.proveedor)
        instance.cliente = validated_data.get('cliente', instance.cliente)
        instance.numero_orden = validated_data.get('numero_orden', instance.numero_orden)
        instance.numero_tracking = validated_data.get('numero_tracking', instance.numero_tracking)
        instance.costo_compra = validated_data.get('costo_compra', instance.costo_compra)
        instance.costo_importacion = validated_data.get('costo_importacion', instance.costo_importacion)
        instance.estado_logistico = validated_data.get('estado_logistico', instance.estado_logistico)

        # When order arrives at store (en_oficina), update unit's estado_producto to en_stock
        if instance.estado_logistico == OrdenCompra.EstadoLogisticoChoices.EN_OFICINA:
            instance.unidad_producto.estado_producto = UnidadProducto.EstadoProductoChoices.EN_STOCK
            instance.unidad_producto.save()

        instance.save()
        return instance
