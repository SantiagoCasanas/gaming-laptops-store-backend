from django.contrib import admin

from .models import AuditLog, Configuracion, Movimiento, PeriodoCalculado, Tramo


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ("id", "capital", "ea", "plazo", "fecha_primer_corte", "activa")


@admin.register(Tramo)
class TramoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "saldo_vigente", "cuota_vigente", "updated_at")


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo", "tramo", "monto", "fecha", "autor")
    list_filter = ("tipo", "tramo")
    date_hierarchy = "fecha"


@admin.register(PeriodoCalculado)
class PeriodoCalculadoAdmin(admin.ModelAdmin):
    list_display = ("mes", "generado_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "accion", "modelo", "objeto_id", "usuario", "timestamp")
    list_filter = ("accion", "modelo")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
