from django.contrib import admin
from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['bill_id', 'cliente', 'concepto', 'item', 'total_amount', 'due_date', 'email_sent', 'active']
    list_filter = ['concepto', 'item', 'payment_method', 'email_sent', 'active']
    search_fields = ['bill_id', 'cliente__nombre_completo', 'cliente__cedula', 'serial_item']
    readonly_fields = ['bill_id', 'file_path', 'email_sent']
    ordering = ['-id']
    raw_id_fields = ['cliente', 'venta', 'separacion']
