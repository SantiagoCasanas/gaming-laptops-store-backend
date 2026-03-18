from django.contrib import admin
from products.models import (
    Brand,
    Category,
    TipoProducto,
    CampoProducto,
    TipoProductoCampo,
    Producto,
    ProductoCategoria,
    ProductoCampoValor,
    ImagenProducto,
    Proveedor,
    UnidadProducto,
    Descuento,
    BajoPedido,
)

# Kept registrations
admin.site.register(Brand)
admin.site.register(Category)

# New model registrations
admin.site.register(TipoProducto)
admin.site.register(CampoProducto)
admin.site.register(TipoProductoCampo)
admin.site.register(Producto)
admin.site.register(ProductoCategoria)
admin.site.register(ProductoCampoValor)
admin.site.register(ImagenProducto)
admin.site.register(Proveedor)
admin.site.register(UnidadProducto)
admin.site.register(Descuento)
admin.site.register(BajoPedido)