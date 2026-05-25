from django.urls import path
from .views import (
    BrandListView,
    BrandCreateView,
    BrandUpdateView,
    BrandActivateView,
    BrandDeactivateView,
    TipoProductoListView,
    TipoProductoCreateView,
    TipoProductoUpdateView,
    TipoProductoActivateView,
    TipoProductoDeactivateView,
    TipoProductoDetailView,
    CampoProductoListView,
    CampoProductoCreateView,
    CampoProductoUpdateView,
    CampoProductoActivateView,
    CampoProductoDeactivateView,
    ProveedorListView,
    ProveedorCreateView,
    ProveedorUpdateView,
    ProveedorActivateView,
    ProveedorDeactivateView,
    ProductoListView,
    ProductoDetailView,
    ProductoCreateView,
    ProductoUpdateView,
    ProductoActivateView,
    ProductoDeactivateView,
    BajoPedidoListView,
    BajoPedidoDetailView,
    BajoPedidoCreateView,
    BajoPedidoUpdateView,
    BajoPedidoActivateView,
    BajoPedidoDeactivateView,
    SyncBajoPedidoLogListView,
    DescuentoActivateView,
    DescuentoDeactivateView,
    DescuentoDeleteView,
    UnidadProductoListView,
    UnidadProductoDetailView,
    UnidadProductoCreateView,
    UnidadProductoUpdateView,
    UnidadProductoActivateView,
    UnidadProductoDeactivateView,
    ReparacionesListView,
    ReportarDanoView,
    IniciarReparacionView,
    CompletarReparacionView,
    MetodoAliadoListView,
    MarcarEnviadaMetodoAliadoView,
    MarcarEntregadaMetodoAliadoView,
    CancelarMetodoAliadoView,
    PlantillaCargueMasivoView,
    CargueMasivoView,
    ConfirmarCargueMasivoView,
    ProductoUploadImagenesView,
    PromoCardsDataView,
    PublicCatalogListView,
    PublicCatalogDetailView,
)

urlpatterns = [
    # Brand endpoints
    path('brands/list/', BrandListView.as_view(), name='brand_list'),
    path('brands/create/', BrandCreateView.as_view(), name='brand_create'),
    path('brands/update/<int:pk>/', BrandUpdateView.as_view(), name='brand_update'),
    path('brands/activate/<int:pk>/', BrandActivateView.as_view(), name='brand_activate'),
    path('brands/deactivate/<int:pk>/', BrandDeactivateView.as_view(), name='brand_deactivate'),

    # Product Type endpoints
    path('product-types/list/', TipoProductoListView.as_view(), name='tipo_producto_list'),
    path('product-types/create/', TipoProductoCreateView.as_view(), name='tipo_producto_create'),
    path('product-types/update/<int:pk>/', TipoProductoUpdateView.as_view(), name='tipo_producto_update'),
    path('product-types/activate/<int:pk>/', TipoProductoActivateView.as_view(), name='tipo_producto_activate'),
    path('product-types/deactivate/<int:pk>/', TipoProductoDeactivateView.as_view(), name='tipo_producto_deactivate'),
    path('product-types/<int:pk>/detail/', TipoProductoDetailView.as_view(), name='tipo_producto_detail'),

    # Product Field endpoints
    path('product-fields/list/', CampoProductoListView.as_view(), name='campo_producto_list'),
    path('product-fields/create/', CampoProductoCreateView.as_view(), name='campo_producto_create'),
    path('product-fields/update/<int:pk>/', CampoProductoUpdateView.as_view(), name='campo_producto_update'),
    path('product-fields/activate/<int:pk>/', CampoProductoActivateView.as_view(), name='campo_producto_activate'),
    path('product-fields/deactivate/<int:pk>/', CampoProductoDeactivateView.as_view(), name='campo_producto_deactivate'),

    # Supplier endpoints
    path('suppliers/list/', ProveedorListView.as_view(), name='proveedor_list'),
    path('suppliers/create/', ProveedorCreateView.as_view(), name='proveedor_create'),
    path('suppliers/update/<int:pk>/', ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('suppliers/activate/<int:pk>/', ProveedorActivateView.as_view(), name='proveedor_activate'),
    path('suppliers/deactivate/<int:pk>/', ProveedorDeactivateView.as_view(), name='proveedor_deactivate'),

    # Public catalog endpoints (Hito 6) — PUBLIC, AllowAny, no auth required
    path('catalogo/', PublicCatalogListView.as_view(), name='catalogo_list'),
    path('catalogo/<int:pk>/', PublicCatalogDetailView.as_view(), name='catalogo_detail'),

    # Producto endpoints
    path('productos/list/', ProductoListView.as_view(), name='producto_list'),
    path('productos/create/', ProductoCreateView.as_view(), name='producto_create'),
    path('productos/update/<int:pk>/', ProductoUpdateView.as_view(), name='producto_update'),
    path('productos/activate/<int:pk>/', ProductoActivateView.as_view(), name='producto_activate'),
    path('productos/deactivate/<int:pk>/', ProductoDeactivateView.as_view(), name='producto_deactivate'),
    path('productos/<int:pk>/detail/', ProductoDetailView.as_view(), name='producto_detail'),

    # BajoPedido endpoints
    path('variantes/list/', BajoPedidoListView.as_view(), name='variante_list'),
    path('variantes/create/', BajoPedidoCreateView.as_view(), name='variante_create'),
    path('variantes/update/<int:pk>/', BajoPedidoUpdateView.as_view(), name='variante_update'),
    path('variantes/activate/<int:pk>/', BajoPedidoActivateView.as_view(), name='variante_activate'),
    path('variantes/deactivate/<int:pk>/', BajoPedidoDeactivateView.as_view(), name='variante_deactivate'),
    path('variantes/<int:pk>/detail/', BajoPedidoDetailView.as_view(), name='variante_detail'),

    # Bajo Pedido daily sync log (read-only monitoring — Hito 7)
    path('sync-bajo-pedido/logs/', SyncBajoPedidoLogListView.as_view(), name='sync_bajo_pedido_logs'),

    # Descuento endpoints
    path('descuentos/activate/<int:pk>/', DescuentoActivateView.as_view(), name='descuento_activate'),
    path('descuentos/deactivate/<int:pk>/', DescuentoDeactivateView.as_view(), name='descuento_deactivate'),
    path('descuentos/delete/<int:pk>/', DescuentoDeleteView.as_view(), name='descuento_delete'),

    # UnidadProducto endpoints
    path('unidades/list/', UnidadProductoListView.as_view(), name='unidad_list'),
    path('unidades/create/', UnidadProductoCreateView.as_view(), name='unidad_create'),
    path('unidades/update/<int:pk>/', UnidadProductoUpdateView.as_view(), name='unidad_update'),
    path('unidades/activate/<int:pk>/', UnidadProductoActivateView.as_view(), name='unidad_activate'),
    path('unidades/deactivate/<int:pk>/', UnidadProductoDeactivateView.as_view(), name='unidad_deactivate'),
    path('unidades/<int:pk>/detail/', UnidadProductoDetailView.as_view(), name='unidad_detail'),

    # Repair pipeline endpoints
    path('reparaciones/list/', ReparacionesListView.as_view(), name='reparacion_list'),
    path('unidades/<int:pk>/reportar-dano/', ReportarDanoView.as_view(), name='unidad_reportar_dano'),
    path('unidades/<int:pk>/iniciar-reparacion/', IniciarReparacionView.as_view(), name='unidad_iniciar_reparacion'),
    path('unidades/<int:pk>/completar-reparacion/', CompletarReparacionView.as_view(), name='unidad_completar_reparacion'),

    # Bulk product upload (template + dry-run preview + commit)
    path('cargue-masivo/plantilla/<int:tipo_producto_id>/', PlantillaCargueMasivoView.as_view(), name='cargue_masivo_plantilla'),
    path('cargue-masivo/', CargueMasivoView.as_view(), name='cargue_masivo'),
    path('cargue-masivo/confirmar/', ConfirmarCargueMasivoView.as_view(), name='cargue_masivo_confirmar'),
    path('productos/<int:pk>/imagenes/upload/', ProductoUploadImagenesView.as_view(), name='producto_imagenes_upload'),

    # Promo cards data (frontend renders the actual images with html2canvas)
    path('promo-cards/data/', PromoCardsDataView.as_view(), name='promo_cards_data'),

    # Método aliado endpoints
    path('metodo-aliado/list/', MetodoAliadoListView.as_view(), name='metodo_aliado_list'),
    path('unidades/<int:pk>/metodo-aliado/marcar-enviada/', MarcarEnviadaMetodoAliadoView.as_view(), name='metodo_aliado_marcar_enviada'),
    path('unidades/<int:pk>/metodo-aliado/marcar-entregada/', MarcarEntregadaMetodoAliadoView.as_view(), name='metodo_aliado_marcar_entregada'),
    path('unidades/<int:pk>/metodo-aliado/cancelar/', CancelarMetodoAliadoView.as_view(), name='metodo_aliado_cancelar'),
]
