from rest_framework import serializers
from .models import TRMHistory


class TRMHistorySerializer(serializers.ModelSerializer):
    """Read-only serializer for TRM history records."""

    class Meta:
        model = TRMHistory
        fields = ['id', 'fecha', 'valor_cop', 'fuente', 'fecha_registro']
        read_only_fields = ['id', 'fecha_registro']


class TRMHistoryCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating TRM history records."""

    class Meta:
        model = TRMHistory
        fields = ['fecha', 'valor_cop', 'fuente']

    def create(self, validated_data):
        # Set default fuente if not provided
        if 'fuente' not in validated_data:
            validated_data['fuente'] = 'superfinanciera'
        return super().create(validated_data)
