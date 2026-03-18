from django.urls import path
from .views import (
    DepartamentoListView,
    CiudadListView,
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDetailView,
    ClienteActivateView,
    ClienteDeactivateView,
    SolicitudBajoPedidoListView,
    SolicitudBajoPedidoCreateView,
    SolicitudBajoPedidoUpdateView,
    SolicitudBajoPedidoDetailView,
    SolicitudBajoPedidoActivateView,
    SolicitudBajoPedidoDeactivateView,
    SeparacionListView,
    SeparacionCreateView,
    SeparacionUpdateView,
    SeparacionDetailView,
    SeparacionActivateView,
    SeparacionDeactivateView,
    VentaListView,
    VentaCreateView,
    VentaDetailView,
    ReciboListView,
    ReciboCreateView,
    ReciboUpdateView,
    ReciboDetailView,
    InvoiceListView,
    InvoiceCreateView,
    InvoiceDetailView,
    InvoiceUpdateView,
    InvoiceDeleteView,
    InvoiceDownloadView,
    InvoiceResendEmailView,
    InvoiceParseNaturalLanguageView,
)

urlpatterns = [
    # Departamento endpoints
    path('departamentos/list/', DepartamentoListView.as_view(), name='departamento_list'),

    # Ciudad endpoints (filterable by departamento)
    path('ciudades/list/', CiudadListView.as_view(), name='ciudad_list'),

    # Cliente endpoints
    path('clientes/list/', ClienteListView.as_view(), name='cliente_list'),
    path('clientes/create/', ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/update/<int:pk>/', ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/detail/<int:pk>/', ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/activate/<int:pk>/', ClienteActivateView.as_view(), name='cliente_activate'),
    path('clientes/deactivate/<int:pk>/', ClienteDeactivateView.as_view(), name='cliente_deactivate'),

    # SolicitudBajoPedido endpoints
    path('productos-bajo-pedido/list/', SolicitudBajoPedidoListView.as_view(), name='producto_bajo_pedido_list'),
    path('productos-bajo-pedido/create/', SolicitudBajoPedidoCreateView.as_view(), name='producto_bajo_pedido_create'),
    path('productos-bajo-pedido/update/<int:pk>/', SolicitudBajoPedidoUpdateView.as_view(), name='producto_bajo_pedido_update'),
    path('productos-bajo-pedido/detail/<int:pk>/', SolicitudBajoPedidoDetailView.as_view(), name='producto_bajo_pedido_detail'),
    path('productos-bajo-pedido/activate/<int:pk>/', SolicitudBajoPedidoActivateView.as_view(), name='producto_bajo_pedido_activate'),
    path('productos-bajo-pedido/deactivate/<int:pk>/', SolicitudBajoPedidoDeactivateView.as_view(), name='producto_bajo_pedido_deactivate'),

    # Separacion endpoints
    path('separaciones/list/', SeparacionListView.as_view(), name='separacion_list'),
    path('separaciones/create/', SeparacionCreateView.as_view(), name='separacion_create'),
    path('separaciones/update/<int:pk>/', SeparacionUpdateView.as_view(), name='separacion_update'),
    path('separaciones/detail/<int:pk>/', SeparacionDetailView.as_view(), name='separacion_detail'),
    path('separaciones/activate/<int:pk>/', SeparacionActivateView.as_view(), name='separacion_activate'),
    path('separaciones/deactivate/<int:pk>/', SeparacionDeactivateView.as_view(), name='separacion_deactivate'),

    # Venta endpoints
    path('ventas/list/', VentaListView.as_view(), name='venta_list'),
    path('ventas/create/', VentaCreateView.as_view(), name='venta_create'),
    path('ventas/detail/<int:pk>/', VentaDetailView.as_view(), name='venta_detail'),

    # Recibo endpoints
    path('recibos/list/', ReciboListView.as_view(), name='recibo_list'),
    path('recibos/create/', ReciboCreateView.as_view(), name='recibo_create'),
    path('recibos/update/<int:pk>/', ReciboUpdateView.as_view(), name='recibo_update'),
    path('recibos/detail/<int:pk>/', ReciboDetailView.as_view(), name='recibo_detail'),

    # Invoice endpoints
    path('invoices/list/', InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/detail/<int:pk>/', InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/update/<int:pk>/', InvoiceUpdateView.as_view(), name='invoice_update'),
    path('invoices/delete/<int:pk>/', InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<int:pk>/download/', InvoiceDownloadView.as_view(), name='invoice_download'),
    path('invoices/<int:pk>/resend_email/', InvoiceResendEmailView.as_view(), name='invoice_resend_email'),
    path('invoices/parse_natural_language/', InvoiceParseNaturalLanguageView.as_view(), name='invoice_parse_nl'),
]
