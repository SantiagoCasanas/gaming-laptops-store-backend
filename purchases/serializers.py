from rest_framework import serializers
from .models import OrdenCompra
from products.models import UnidadProducto, Proveedor, BajoPedido, Producto


class OrdenCompraSerializer(serializers.ModelSerializer):
    """
    Serializer for OrdenCompra model.
    Used for listing and retrieving purchase order information.
    """
    unidad_serial = serializers.CharField(source='unidad_producto.serial', read_only=True)
    unidad_precio = serializers.DecimalField(source='unidad_producto.precio', max_digits=14, decimal_places=2, read_only=True, allow_null=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    condicion_display = serializers.CharField(source='get_condicion_display', read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True, allow_null=True)
    impuesto_importacion = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrdenCompra
        fields = [
            'id', 'producto', 'producto_nombre', 'condicion', 'condicion_display',
            'unidad_producto', 'unidad_serial', 'unidad_precio', 'estado_logistico',
            'proveedor', 'proveedor_nombre',
            'numero_orden', 'numero_tracking', 'costo_compra',
            'costo_importacion', 'impuesto_importacion', 'active'
        ]


class OrdenCompraCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new purchase order.
    Automatically creates a UnidadProducto when the order is created.
    precio_venta is write-only: if provided it overrides the auto-calculated unit price;
    if omitted the unit price is calculated from costs and TRM.
    """
    precio_venta = serializers.DecimalField(
        max_digits=14, decimal_places=2,
        write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model = OrdenCompra
        fields = [
            'producto', 'condicion', 'proveedor',
            'numero_orden', 'numero_tracking', 'costo_compra',
            'costo_importacion', 'estado_logistico', 'precio_venta',
        ]

    def validate(self, attrs):
        """Ensure proveedor is provided."""
        if not attrs.get('proveedor'):
            raise serializers.ValidationError("A supplier (proveedor) is required")
        return attrs

    def create(self, validated_data):
        """Create purchase order. UnidadProducto is auto-created via OrdenCompra.save().
        If precio_venta was supplied, override the auto-calculated unit price."""
        precio_venta = validated_data.pop('precio_venta', None)
        orden = OrdenCompra.objects.create(
            usuario_ultima_modificacion=self.context.get('request').user if self.context.get('request') else None,
            **validated_data
        )
        if precio_venta and orden.unidad_producto:
            orden.unidad_producto.precio = precio_venta
            orden.unidad_producto.save()
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
            'proveedor', 'numero_orden',
            'numero_tracking', 'costo_compra', 'costo_importacion', 'impuesto_importacion',
            'estado_logistico'
        ]

    def update(self, instance, validated_data):
        """Update and return the purchase order instance."""
        instance.proveedor = validated_data.get('proveedor', instance.proveedor)
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
