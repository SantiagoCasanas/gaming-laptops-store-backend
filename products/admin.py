from django.contrib import admin
from products.models import *

# Register your models here.
admin.site.register(Brand)
admin.site.register(Category)
admin.site.register(BaseProduct)
admin.site.register(ProductVariant)
admin.site.register(Image)
admin.site.register(Discount)