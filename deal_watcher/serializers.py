"""DRF serializers for the Deal Watcher admin API."""
from django.conf import settings
from rest_framework import serializers

from .models import (
    ConfiguracionNotificador,
    MonitoredProduct,
    NotificationPause,
    PriceCheck,
    TelegramSubscriber,
    TrustedSeller,
)


# ---------------------------------------------------------------------------
# TrustedSeller
# ---------------------------------------------------------------------------

class TrustedSellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustedSeller
        fields = ['id', 'username', 'display_name', 'notes', 'active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrustedSellerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustedSeller
        fields = ['username', 'display_name', 'notes']


class TrustedSellerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustedSeller
        fields = ['username', 'display_name', 'notes']


# ---------------------------------------------------------------------------
# ConfiguracionNotificador (singleton)
# ---------------------------------------------------------------------------

class ConfiguracionNotificadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionNotificador
        fields = [
            'id', 'hora_inicio_activa', 'hora_fin_activa',
            'llamados_diarios_objetivo', 'reserva_otros_llamados',
            'active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConfiguracionNotificadorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionNotificador
        fields = [
            'hora_inicio_activa', 'hora_fin_activa',
            'llamados_diarios_objetivo', 'reserva_otros_llamados', 'active',
        ]

    def validate(self, attrs):
        # Combinar con la instancia para soportar PATCH parcial.
        objetivo = attrs.get(
            'llamados_diarios_objetivo',
            getattr(self.instance, 'llamados_diarios_objetivo', None),
        )
        reserva = attrs.get(
            'reserva_otros_llamados',
            getattr(self.instance, 'reserva_otros_llamados', None),
        )
        tope = getattr(settings, 'EBAY_LLAMADOS_DIARIOS_MAX', 5000)
        if objetivo is not None and objetivo > tope:
            raise serializers.ValidationError(
                {'llamados_diarios_objetivo': f"No puede superar el tope de eBay ({tope})."}
            )
        if objetivo is not None and reserva is not None and reserva >= objetivo:
            raise serializers.ValidationError(
                {'reserva_otros_llamados': "La reserva debe ser menor que el presupuesto diario."}
            )
        return attrs


class NotificadorStatusSerializer(serializers.Serializer):
    """Snapshot read-only del estado del pacing (para la página admin)."""
    enabled = serializers.BooleanField()
    within_window = serializers.BooleanField()
    period = serializers.DateField(allow_null=True)
    window_label = serializers.CharField()
    objetivo = serializers.IntegerField()
    reserva = serializers.IntegerField()
    effective_budget = serializers.IntegerField()
    earned = serializers.FloatField()
    used = serializers.IntegerField()
    n_products = serializers.IntegerField()
    cycles_today = serializers.IntegerField()
    last_run_at = serializers.DateTimeField(allow_null=True)
    cadencia_estimada_min = serializers.FloatField(allow_null=True)
    cadencia_efectiva_min = serializers.FloatField(allow_null=True)


# ---------------------------------------------------------------------------
# MonitoredProduct
# ---------------------------------------------------------------------------

class MonitoredProductSerializer(serializers.ModelSerializer):
    producto_catalogo_nombre = serializers.CharField(source='producto_catalogo.nombre', read_only=True, default='')

    class Meta:
        model = MonitoredProduct
        fields = [
            'id',
            'nickname',
            'ebay_url',
            'ebay_item_id',
            'max_price_cop',
            'producto_catalogo',
            'producto_catalogo_nombre',
            'last_seen_available_at',
            'last_notified_at',
            'last_notified_price_usd',
            'last_known_price_usd',
            'last_known_seller',
            'active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'ebay_item_id',
            'last_seen_available_at',
            'last_notified_at',
            'last_notified_price_usd',
            'last_known_price_usd',
            'last_known_seller',
            'created_at',
            'updated_at',
        ]


def _validate_ebay_url(value: str) -> str:
    """Reject URLs the parser cannot extract a legacy id from — early 400."""
    from products.services.ebay_service import extract_legacy_id_from_url
    try:
        extract_legacy_id_from_url(value)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc))
    return value


class MonitoredProductCreateSerializer(serializers.ModelSerializer):
    """Operator only provides URL + ceiling. The item id is derived on save()."""
    class Meta:
        model = MonitoredProduct
        fields = ['nickname', 'ebay_url', 'max_price_cop', 'producto_catalogo']

    def validate_ebay_url(self, value):
        return _validate_ebay_url(value)

    def create(self, validated_data):
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            validated_data['usuario_ultima_modificacion'] = request.user
        return super().create(validated_data)


class MonitoredProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoredProduct
        fields = ['nickname', 'ebay_url', 'max_price_cop', 'producto_catalogo']

    def validate_ebay_url(self, value):
        return _validate_ebay_url(value)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            validated_data['usuario_ultima_modificacion'] = request.user
        return super().update(instance, validated_data)


# ---------------------------------------------------------------------------
# PriceCheck (history, read-only)
# ---------------------------------------------------------------------------

class PriceCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceCheck
        fields = [
            'id',
            'monitored_product',
            'checked_at',
            'was_available',
            'price_usd',
            'trm_used',
            'price_cop_calculated',
            'seller_username',
            'seller_is_trusted',
            'triggered_notification',
            'error_message',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# NotificationPause
# ---------------------------------------------------------------------------

class NotificationPauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPause
        fields = [
            'id',
            'scope',
            'monitored_product',
            'paused_until',
            'reason',
            'created_via',
            'active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_via', 'created_at', 'updated_at']


class GlobalPauseCreateSerializer(serializers.Serializer):
    """
    Input for `POST /pauses/global/create/`.

    Either `paused_until` (ISO datetime) or `duration_minutes` may be given.
    Both null → indefinite pause.
    """
    paused_until = serializers.DateTimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs.get('paused_until') and attrs.get('duration_minutes'):
            raise serializers.ValidationError(
                "Provide either 'paused_until' or 'duration_minutes', not both."
            )
        return attrs


class GlobalPauseStatusSerializer(serializers.Serializer):
    """Output for `GET /pauses/global/status/`."""
    is_paused = serializers.BooleanField()
    paused_until = serializers.DateTimeField(allow_null=True)
    reason = serializers.CharField(allow_blank=True)
    created_via = serializers.CharField(allow_blank=True)


# ---------------------------------------------------------------------------
# TelegramSubscriber (read-only listing for the admin UI)
# ---------------------------------------------------------------------------

class TelegramSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramSubscriber
        fields = ['id', 'chat_id', 'telegram_username', 'active', 'first_seen_at']
        read_only_fields = fields
