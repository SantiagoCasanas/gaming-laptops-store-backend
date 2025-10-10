import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from core.models import BaseModel

def get_image_upload_path(instance, filename):
    """Generates a unique path for every image."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f'products/images/{filename}'


class Brand(BaseModel):
    """Model that represents a brand, ej: ASUS, MSI, NVIDIA."""
    name = models.CharField(max_length=100, null=False, unique=True, help_text="Brand's name")
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL slug, auto-generated")

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(BaseModel):
    """Model that represents the product's category, ej: Portátiles, Tarjetas Gráficas."""
    name = models.CharField(max_length=100, unique=True, null=False, help_text="Categorys name")
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL slug, auto-generated")
    description = models.TextField(blank=True, null=True, help_text="Optional description of the category")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BaseProduct(BaseModel):
    """Base model that contains the product's base info."""
    model_name = models.CharField(max_length=255, null=False, help_text="Full name of the product model")
    slug = models.SlugField(max_length=280, unique=True, blank=True, null=False, help_text="Slug for the URL, it is automatically generated")
    long_description = models.TextField(null=False, help_text="Detailed description and specifications of the product")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="base_products", null=False, help_text="Brand to which the product belongs")
    categories = models.ManyToManyField(Category, related_name="base_products", help_text="Categories to which the product belongs")
    specs = models.JSONField(default=dict, null=False, help_text="Product specifications in JSON format")
    user_last_modified = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        help_text="Last user who modified this product"
    )
    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
 

    class Meta:
        verbose_name = "Base Product"
        verbose_name_plural = "Base Products"
        ordering = ['-user_last_modified']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand.name}-{self.model_name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand.name} - {self.model_name}"


class ProductVariant(BaseModel):
    """Represents a specific variant of a BaseProduct, differentiated by condition, stock status, price, etc."""
    class ConditionChoices(models.TextChoices):
        NEW = 'nuevo', 'Nuevo'
        OPEN_BOX = 'open_box', 'Open Box'
        REFURBISHED = 'refurbished', 'Refurbished'
        USED = 'usado', 'Usado'

    class StatusStockChoices(models.TextChoices):
        IN_STOCK = 'en_stock', 'En Stock'
        ON_THE_WAY = 'en_camino', 'En Camino'
        WITH_IMPORTATION = 'por_importacion', 'Por Importación'
        WITHOUT_STOCK = 'sin_stock', 'Sin Stock'

    base_product = models.ForeignKey(BaseProduct, on_delete=models.PROTECT, related_name="product_variants", help_text="Base product to which this variant belongs")
    price = models.IntegerField(null=False, help_text="Selling price of the variant")
    description = models.TextField(null=True, blank=True, help_text="Specific description for this variant (e.g., 'Open box, unused equipment')")
    condition = models.CharField(null=False, max_length=20, choices=ConditionChoices.choices, default=ConditionChoices.NEW, help_text="Condition of the product")
    stock_status = models.CharField(null=False, max_length=20, choices=StatusStockChoices.choices, default=StatusStockChoices.IN_STOCK, help_text="Product stock status")
    is_publishied = models.BooleanField(default=True, null=False, help_text="Indicates whether the variant is visible in the store")
    user_last_modified = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        help_text="Last user who modified this variant"
    )
    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        ordering = ['price', 'condition']

    def __str__(self):
        return f"{self.base_product.model_name} ({self.get_condition_display()}) - {self.pk}"


class Image(BaseModel):
    """Model to save the images that belongs to the product."""
    product_variant = models.ForeignKey(BaseProduct, on_delete=models.ProtectedError, related_name="images", help_text="Variant to which the image belongs")
    imagen = models.ImageField(upload_to=get_image_upload_path, help_text="Product' image")
    alt_text = models.CharField(max_length=255, blank=True, null=True, help_text="Texto alternativo para la imagen (SEO)")

    class Meta:
        verbose_name = "Imagen"
        verbose_name_plural = "Images"

    def __str__(self):
        return f"Image for {self.product_variant.pk}"
    

class Discount(models.Model):
    """Model for applying a discount to a ProductVariant."""
    product_variant = models.OneToOneField(ProductVariant, on_delete=models.PROTECT, related_name="discount", help_text="Variant that has this discount")
    discount_price = models.IntegerField(null=False, help_text="Final price with discount applied")
    active = models.BooleanField(default=True, help_text="Indicates whether the discount is active")

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"

    def __str__(self):
        status = "Active" if self.active else "Inactive"
        return f"Discount for {self.product_variant} - ${self.discount_price} ({status})"
