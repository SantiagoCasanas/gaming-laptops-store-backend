from decimal import Decimal
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
            'costo_importacion', 'impuesto_importacion',
            'fecha_compra', 'fecha_estimada_llegada', 'active'
        ]


class OrdenCompraCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new purchase order.
    porcentaje_impuesto is write-only and transient: not stored in DB, used to calculate
    impuesto_importacion via OrdenCompra.save() through the _pct_impuesto instance attribute.
    precio_venta is write-only: if provided it overrides the auto-calculated unit price.
    """
    precio_venta = serializers.DecimalField(
        max_digits=14, decimal_places=2,
        write_only=True, required=False, allow_null=True,
    )
    porcentaje_impuesto = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        write_only=True, required=False, default=Decimal('2'),
    )

    class Meta:
        model = OrdenCompra
        fields = [
            'producto', 'condicion', 'proveedor',
            'numero_orden', 'numero_tracking', 'costo_compra',
            'costo_importacion', 'porcentaje_impuesto', 'estado_logistico', 'precio_venta',
            'fecha_compra',
        ]

    def validate(self, attrs):
        if not attrs.get('proveedor'):
            raise serializers.ValidationError("A supplier (proveedor) is required")
        return attrs

    def create(self, validated_data):
        precio_venta = validated_data.pop('precio_venta', None)
        pct = validated_data.pop('porcentaje_impuesto', Decimal('2'))

        orden = OrdenCompra(
            usuario_ultima_modificacion=self.context.get('request').user if self.context.get('request') else None,
            **validated_data
        )
        orden._pct_impuesto = pct
        orden.save()

        if precio_venta and orden.unidad_producto:
            orden.unidad_producto.precio = precio_venta
            orden.unidad_producto.save()

        return orden


class OrdenCompraUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating purchase order information.
    porcentaje_impuesto is write-only and transient: recalculates impuesto_importacion on save.
    impuesto_importacion is read-only (always auto-calculated).
    """
    impuesto_importacion = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    porcentaje_impuesto = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model = OrdenCompra
        fields = [
            'proveedor', 'numero_orden',
            'numero_tracking', 'costo_compra', 'costo_importacion',
            'porcentaje_impuesto', 'impuesto_importacion',
            'estado_logistico', 'fecha_compra',
        ]

    def update(self, instance, validated_data):
        pct = validated_data.pop('porcentaje_impuesto', None)

        instance.proveedor = validated_data.get('proveedor', instance.proveedor)
        instance.numero_orden = validated_data.get('numero_orden', instance.numero_orden)
        instance.numero_tracking = validated_data.get('numero_tracking', instance.numero_tracking)
        instance.costo_compra = validated_data.get('costo_compra', instance.costo_compra)
        instance.costo_importacion = validated_data.get('costo_importacion', instance.costo_importacion)
        instance.estado_logistico = validated_data.get('estado_logistico', instance.estado_logistico)
        instance.fecha_compra = validated_data.get('fecha_compra', instance.fecha_compra)

        if pct is not None:
            instance._pct_impuesto = pct

        # When order arrives at store (en_oficina), update unit's estado_producto to en_stock
        if instance.estado_logistico == OrdenCompra.EstadoLogisticoChoices.EN_OFICINA:
            instance.unidad_producto.estado_producto = UnidadProducto.EstadoProductoChoices.EN_STOCK
            instance.unidad_producto.save()

        instance.save()
        return instance
