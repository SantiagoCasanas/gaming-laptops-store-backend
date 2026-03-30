from django.contrib import admin
from products.models import (
    Brand,
    TipoProducto,
    CampoProducto,
    TipoProductoCampo,
    Producto,
    ProductoCampoValor,
    ImagenProducto,
    Proveedor,
    UnidadProducto,
    Descuento,
    BajoPedido,
)

# Kept registrations
admin.site.register(Brand)

# New model registrations
admin.site.register(TipoProducto)
admin.site.register(CampoProducto)
admin.site.register(TipoProductoCampo)
admin.site.register(Producto)
admin.site.register(ProductoCampoValor)
admin.site.register(ImagenProducto)
admin.site.register(Proveedor)
admin.site.register(UnidadProducto)
admin.site.register(Descuento)
admin.site.register(BajoPedido)
