from django.contrib import admin
from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['bill_id', 'client_name', 'concepto', 'item', 'total_amount', 'due_date', 'email_sent', 'created_at']
    list_filter = ['concepto', 'item', 'payment_method', 'email_sent']
    search_fields = ['bill_id', 'client_name', 'client_email', 'serial_item']
    readonly_fields = ['bill_id', 'file_path', 'email_sent', 'created_at', 'updated_at']
    ordering = ['-created_at']
