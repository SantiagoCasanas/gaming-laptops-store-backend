"""Rutas de la app `prestamo`. Montadas bajo /api/prestamo/ en config/urls.py."""

from django.urls import path

from . import views

urlpatterns = [
    path("resumen/", views.ResumenView.as_view(), name="prestamo-resumen"),
    path("proyeccion/", views.ProyeccionView.as_view(), name="prestamo-proyeccion"),
    path("movimientos/", views.MovimientoListCreateView.as_view(), name="prestamo-movimientos"),
    path("movimientos/<int:pk>/", views.MovimientoDetailView.as_view(), name="prestamo-movimiento-detail"),
    path("pago-regular/", views.PagoRegularView.as_view(), name="prestamo-pago-regular"),
    path("comprobantes/", views.ComprobanteUploadView.as_view(), name="prestamo-comprobantes"),
    path("auditoria/", views.AuditoriaListView.as_view(), name="prestamo-auditoria"),
    path("configuracion/", views.ConfiguracionView.as_view(), name="prestamo-configuracion"),
]
