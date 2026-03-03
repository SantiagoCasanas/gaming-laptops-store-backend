from rest_framework import serializers
from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    bill_id = serializers.CharField(read_only=True)
    file_path = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'bill_id',
            'client_name',
            'client_document',
            'client_phone',
            'client_address',
            'client_email',
            'concepto',
            'item',
            'serial_item',
            'total_amount',
            'payment_method',
            'due_date',
            'file_path',
            'email_sent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'bill_id', 'file_path', 'email_sent', 'created_at', 'updated_at']

    def validate(self, attrs):
        required_fields = [
            'client_name', 'client_document', 'client_phone',
            'client_address', 'client_email', 'concepto', 'item',
            'serial_item', 'total_amount', 'payment_method', 'due_date',
        ]
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
            'client_name',
            'client_document',
            'client_phone',
            'client_address',
            'client_email',
            'concepto',
            'item',
            'serial_item',
            'total_amount',
            'payment_method',
            'due_date',
        ]
