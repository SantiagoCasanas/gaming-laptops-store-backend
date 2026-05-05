"""
Output-only serializers for the dashboard endpoints. Each mirrors the JSON
contract documented in services.py and the spec, providing schema discipline
and consistent decimal/null formatting at the API edge.
"""

from rest_framework import serializers


class _DeltaKpiSerializer(serializers.Serializer):
    valor = serializers.DecimalField(max_digits=20, decimal_places=2)
    delta_pct = serializers.FloatField(allow_null=True)


class _PendingSalesSerializer(serializers.Serializer):
    valor = serializers.IntegerField()
    atrasadas_2_dias = serializers.IntegerField()


class _InventarioSerializer(serializers.Serializer):
    valor = serializers.DecimalField(max_digits=20, decimal_places=2)
    cantidad_equipos = serializers.IntegerField()


class _ViajandoSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField()
    valor_en_camino = serializers.DecimalField(max_digits=20, decimal_places=2)


class _EstadoReparacionSerializer(serializers.Serializer):
    en_reparacion = serializers.IntegerField()
    por_reparar = serializers.IntegerField()


class _OrigenDanoSerializer(serializers.Serializer):
    garantia = serializers.IntegerField()
    stock = serializers.IntegerField()


class _DanadosSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    estado_reparacion = _EstadoReparacionSerializer()
    origen_dano = _OrigenDanoSerializer()


class KpisSerializer(serializers.Serializer):
    ventas_mes = _DeltaKpiSerializer()
    ganancia_neta = _DeltaKpiSerializer()
    ordenes_por_entregar = _PendingSalesSerializer()
    valor_inventario = _InventarioSerializer()
    equipos_viajando = _ViajandoSerializer()
    equipos_danados = _DanadosSerializer()


class TimelinePointSerializer(serializers.Serializer):
    dia = serializers.IntegerField()
    valor = serializers.DecimalField(max_digits=20, decimal_places=2)


class SalesTimelineSerializer(serializers.Serializer):
    actual = TimelinePointSerializer(many=True)
    anterior = TimelinePointSerializer(many=True)


class SalesOrdersStatusSerializer(serializers.Serializer):
    por_entregar = serializers.IntegerField()
    entregado = serializers.IntegerField()


class PurchaseOrdersStatusSerializer(serializers.Serializer):
    viajando = serializers.IntegerField()
    en_oficina_importadora = serializers.IntegerField()
    en_oficina = serializers.IntegerField()


class ReservationSerializer(serializers.Serializer):
    tipo = serializers.CharField(allow_null=True)
    serial = serializers.CharField(allow_null=True)
    cliente = serializers.CharField(allow_null=True)
    dias = serializers.IntegerField()


class ImportsExpenseRowSerializer(serializers.Serializer):
    mes = serializers.CharField()
    valor_importacion = serializers.DecimalField(max_digits=20, decimal_places=2)
    impuesto = serializers.DecimalField(max_digits=20, decimal_places=2)
