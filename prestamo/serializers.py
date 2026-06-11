"""Serializers de la app `prestamo`."""

from decimal import Decimal

from rest_framework import serializers

from .models import AuditLog, Configuracion, Movimiento, Tramo

# Tramo implícito según el tipo de movimiento.
_TRAMO_POR_TIPO = {
    Movimiento.CUOTA_AMIGO: Tramo.AMIGO,
    Movimiento.ABONO_AMIGO: Tramo.AMIGO,
    Movimiento.COMISION: Tramo.AMIGO,
    Movimiento.CUOTA_DUENO: Tramo.DUENO,
    Movimiento.ABONO_DUENO: Tramo.DUENO,
}


class MovimientoSerializer(serializers.ModelSerializer):
    """Lectura de movimientos (incluye datos del autor)."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    autor_email = serializers.EmailField(source="autor.email", read_only=True, default=None)

    class Meta:
        model = Movimiento
        fields = [
            "id", "tipo", "tipo_display", "tramo", "monto", "fecha",
            "autor", "autor_email", "nota", "comprobante_url",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "autor", "created_at", "updated_at"]


class MovimientoWriteSerializer(serializers.ModelSerializer):
    """Crear/editar movimientos. `tramo` es opcional: se deriva del tipo."""

    tramo = serializers.ChoiceField(
        choices=Tramo.TRAMO_CHOICES, required=False, allow_blank=True
    )

    class Meta:
        model = Movimiento
        fields = ["tipo", "tramo", "monto", "fecha", "nota", "comprobante_url"]

    def validate_monto(self, value):
        if value is None or value <= Decimal("0"):
            raise serializers.ValidationError("El monto debe ser mayor que 0.")
        return value

    def validate(self, attrs):
        tipo = attrs.get("tipo") or getattr(self.instance, "tipo", None)
        tramo = attrs.get("tramo")
        esperado = _TRAMO_POR_TIPO.get(tipo)
        if not tramo:
            attrs["tramo"] = esperado
        elif esperado and tramo != esperado:
            raise serializers.ValidationError(
                {"tramo": f"El tipo '{tipo}' corresponde al tramo '{esperado}'."}
            )
        return attrs


class TramoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tramo
        fields = ["nombre", "saldo_vigente", "cuota_vigente", "updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True, default=None)
    accion_display = serializers.CharField(source="get_accion_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "usuario", "usuario_email", "accion", "accion_display",
            "modelo", "objeto_id", "valores_antes", "valores_despues", "timestamp",
        ]


class ConfiguracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuracion
        fields = [
            "id", "capital", "ea", "i_m", "plazo", "dia_corte",
            "mes_renegociacion", "comision_pct", "saldo_dueno",
            "saldo_amigo_reneg", "fecha_primer_corte", "activa",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
