import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from core.models import BaseModel


# ---------------------------------------------------------------------------
# Legacy upload helper — kept so existing migrations (0001_initial) can load.
# Not used by any current model.
# ---------------------------------------------------------------------------

def get_image_upload_path(instance, filename):
    """Legacy upload path helper referenced by early migrations."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f'products/images/{filename}'


# ---------------------------------------------------------------------------
# Kept models (Brand, Category) — no structural changes
# ---------------------------------------------------------------------------

class Brand(BaseModel):
    """Model that represents a brand, e.g.: ASUS, MSI, NVIDIA."""
    name = models.CharField(max_length=100, null=False, unique=True, help_text="Brand's name")
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL slug, auto-generated")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

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
    """Model that represents the product's category, e.g.: Portátiles, Tarjetas Gráficas."""
    name = models.CharField(max_length=100, unique=True, null=False, help_text="Category's name")
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL slug, auto-generated")
    description = models.TextField(blank=True, null=True, help_text="Optional description of the category")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

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


# ---------------------------------------------------------------------------
# New domain models — Patecnologicos-bd schema
# ---------------------------------------------------------------------------

class TipoProducto(BaseModel):
    """
    Defines a product type (e.g. Laptop, GPU, Peripheral).
    Acts as a template that declares which dynamic fields apply to products of that type.
    """
    nombre = models.CharField(max_length=100, unique=True, null=False, help_text="Product type name")
    descripcion = models.TextField(blank=True, null=True, help_text="Optional description of the product type")

    class Meta:
        verbose_name = "Product Type"
        verbose_name_plural = "Product Types"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class CampoProducto(BaseModel):
    """
    Defines a dynamic field that can be attached to one or more product types.
    Supports three data types: text, number, and boolean.
    """
    class TipoCampoChoices(models.TextChoices):
        TEXTO = 'texto', 'Text'
        NUMERO = 'numero', 'Number'
        BOOLEANO = 'booleano', 'Boolean'

    nombre = models.CharField(max_length=100, unique=True, null=False, help_text="Field name (e.g. RAM, GPU Model)")
    tipo = models.CharField(
        max_length=20,
        choices=TipoCampoChoices.choices,
        default=TipoCampoChoices.TEXTO,
        null=False,
        help_text="Data type of this field"
    )
    required = models.BooleanField(
        default=False,
        help_text="Whether this field must be filled in when creating or editing a product"
    )

    class Meta:
        verbose_name = "Product Field"
        verbose_name_plural = "Product Fields"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class TipoProductoCampo(models.Model):
    """
    Junction table that associates CampoProducto instances to a TipoProducto.
    Includes an ordering field to control display order of fields per product type,
    and a required flag that controls whether the field is mandatory when creating
    or editing a product of this type (Option B: required is per-association,
    not per-field globally).
    """
    tipo_producto = models.ForeignKey(
        TipoProducto,
        on_delete=models.CASCADE,
        related_name='tipo_producto_campos',
        help_text="Product type this field belongs to"
    )
    campo_producto = models.ForeignKey(
        CampoProducto,
        on_delete=models.CASCADE,
        related_name='tipo_producto_campos',
        help_text="Dynamic field linked to this product type"
    )
    orden = models.PositiveIntegerField(default=0, help_text="Display order of this field within the product type")
    required = models.BooleanField(
        default=False,
        help_text="Whether this field is required when creating or editing a product of this type"
    )

    class Meta:
        verbose_name = "Product Type Field"
        verbose_name_plural = "Product Type Fields"
        ordering = ['orden']
        unique_together = [('tipo_producto', 'campo_producto')]

    def __str__(self):
        req = " [required]" if self.required else ""
        return f"{self.tipo_producto.nombre} -> {self.campo_producto.nombre} (orden {self.orden}){req}"


class Producto(BaseModel):
    """
    Core product entity. Represents a single product model (not a purchasable listing).
    Linked to a brand, a product type, and one or more categories.
    """
    nombre = models.CharField(max_length=255, null=False, help_text="Full product name / model")
    descripcion = models.TextField(null=False, help_text="Detailed product description (supports long text with formatting)")
    marca = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='productos',
        null=False,
        help_text="Brand of this product"
    )
    tipo_producto = models.ForeignKey(
        TipoProducto,
        on_delete=models.PROTECT,
        related_name='productos',
        null=False,
        help_text="Product type that defines which dynamic fields apply"
    )
    categorias = models.ManyToManyField(
        Category,
        through='ProductoCategoria',
        related_name='productos',
        help_text="Categories this product belongs to"
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        help_text="Last user who modified this product"
    )

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-id']

    def __str__(self):
        return f"{self.marca.name} - {self.nombre}"


class ProductoCategoria(models.Model):
    """
    Explicit junction table for the Producto <-> Category M2M relationship.
    """
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='producto_categorias',
        help_text="Product"
    )
    categoria = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='producto_categorias',
        help_text="Category"
    )

    class Meta:
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        unique_together = [('producto', 'categoria')]

    def __str__(self):
        return f"{self.producto.nombre} -> {self.categoria.name}"


class ProductoCampoValor(models.Model):
    """
    Stores the actual value of a dynamic CampoProducto for a specific Producto.
    Only one of the three value columns is expected to be non-null per row,
    depending on CampoProducto.tipo.
    """
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='campo_valores',
        help_text="Product this value belongs to"
    )
    campo_producto = models.ForeignKey(
        CampoProducto,
        on_delete=models.PROTECT,
        related_name='campo_valores',
        help_text="Dynamic field definition"
    )
    valor_texto = models.TextField(blank=True, null=True, help_text="Value when campo_producto.tipo = 'texto'")
    valor_numero = models.DecimalField(
        max_digits=20, decimal_places=6,
        blank=True, null=True,
        help_text="Value when campo_producto.tipo = 'numero'"
    )
    valor_booleano = models.BooleanField(blank=True, null=True, help_text="Value when campo_producto.tipo = 'booleano'")

    class Meta:
        verbose_name = "Product Field Value"
        verbose_name_plural = "Product Field Values"
        unique_together = [('producto', 'campo_producto')]

    def __str__(self):
        return f"{self.producto.nombre} - {self.campo_producto.nombre}"


class ImagenProducto(BaseModel):
    """
    Image associated with a Producto. Stores a URL/path and a display order.
    """
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='imagenes',
        help_text="Product this image belongs to"
    )
    url = models.ImageField(
        upload_to='products/images/',
        null=False,
        help_text="Product image file"
    )
    orden = models.PositiveSmallIntegerField(default=0, help_text="Display order of this image")

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ['orden']

    def __str__(self):
        return f"Image #{self.orden} - {self.producto.nombre}"


class Proveedor(BaseModel):
    """
    Supplier / vendor entity. Referenced by BajoPedido to track the source.
    """
    nombre = models.CharField(max_length=100, unique=True, null=False, help_text="Supplier name")
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL slug, auto-generated")

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class BajoPedido(BaseModel):
    """
    Represents a product available on-demand (e.g., via eBay).
    Not a real unit - updated daily by Celery based on supplier availability.
    """
    class CondicionChoices(models.TextChoices):
        NUEVO = 'nuevo', 'New'
        OPEN_BOX = 'open_box', 'Open Box'
        REFURBISHED = 'refurbished', 'Refurbished'
        USADO = 'usado', 'Used'

    class EstadoChoices(models.TextChoices):
        ACTIVO = 'activo', 'Active'
        SIN_EXISTENCIAS = 'sin_existencias', 'Out of Stock'
        INACTIVO = 'inactivo', 'Inactive'

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='bajo_pedidos',
        help_text="Product available on-demand"
    )
    condicion = models.CharField(
        max_length=20,
        choices=CondicionChoices.choices,
        help_text="Physical condition for on-demand sourcing"
    )
    precio = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="Price updated daily by Celery via eBay formula"
    )
    enlace_proveedor = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="eBay item URL (optional)"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.ACTIVO,
        help_text="Availability status for on-demand sourcing"
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        related_name='bajo_pedidos',
        null=True,
        blank=True,
        help_text="Supplier (optional)"
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name='bajo_pedidos_modificados',
        help_text="Last user who modified this record"
    )

    class Meta:
        verbose_name = "On-Demand Product"
        verbose_name_plural = "On-Demand Products"
        unique_together = [('producto', 'condicion')]
        ordering = ['producto', 'condicion']

    def __str__(self):
        return f"{self.producto.nombre} ({self.condicion}) - ${self.precio} ({self.get_estado_display()})"


class UnidadProducto(BaseModel):
    """
    Represents a single physical unit of a Producto.
    Tracks serial number, sale state, physical state, condition, and individual price.
    """
    class CondicionChoices(models.TextChoices):
        NUEVO = 'nuevo', 'New'
        OPEN_BOX = 'open_box', 'Open Box'
        REFURBISHED = 'refurbished', 'Refurbished'
        USADO = 'usado', 'Used'

    class EstadoVentaChoices(models.TextChoices):
        SIN_VENDER = 'sin_vender', 'Not Sold'
        SEPARADO = 'separado', 'On Hold'
        VENDIDO = 'vendido', 'Sold'
        POR_ENCARGO = 'por_encargo', 'On Order'
        ENTREGADO_GARANTIA = 'entregado_garantia', 'Warranty Delivery'
        DANADO = 'danado', 'Damaged'
        SOLICITUD_METODO_ALIADO = 'solicitud_metodo_aliado', 'Pending Trade-in'

    class EstadoProductoChoices(models.TextChoices):
        EN_STOCK = 'en_stock', 'In Stock'
        VIAJANDO = 'viajando', 'In Transit'
        POR_COMPRAR = 'por_comprar', 'Pending Purchase'
        POR_ENTREGAR = 'por_entregar', 'Pending Delivery'
        ENTREGADO = 'entregado', 'Delivered'
        POR_REPARAR = 'por_reparar', 'Pending Repair'
        EN_REPARACION = 'en_reparacion', 'In Repair'

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='unidades',
        null=False,
        help_text="Product this unit belongs to"
    )
    serial = models.CharField(max_length=100, unique=True, null=False, help_text="Unique serial number of this unit")
    condicion = models.CharField(
        max_length=20,
        choices=CondicionChoices.choices,
        null=False,
        help_text="Physical condition of this unit"
    )
    estado_venta = models.CharField(
        max_length=30,
        choices=EstadoVentaChoices.choices,
        default=EstadoVentaChoices.SIN_VENDER,
        null=False,
        help_text="Commercial status of this unit"
    )
    estado_producto = models.CharField(
        max_length=20,
        choices=EstadoProductoChoices.choices,
        default=EstadoProductoChoices.EN_STOCK,
        null=False,
        help_text="Physical / logistic state of this unit"
    )
    precio = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=False,
        help_text="Individual sale price for this unit (COP)"
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name='unidades_modificadas',
        help_text="Last user who modified this unit"
    )

    class Meta:
        verbose_name = "Product Unit"
        verbose_name_plural = "Product Units"
        ordering = ['serial']

    def __str__(self):
        return f"Unit {self.serial} - {self.producto.nombre} ({self.condicion})"


class Descuento(BaseModel):
    """
    Discount applied to a product with specific condition.
    Applies to all sin_vender units matching (producto, condicion).
    """
    class CondicionChoices(models.TextChoices):
        NUEVO = 'nuevo', 'New'
        OPEN_BOX = 'open_box', 'Open Box'
        REFURBISHED = 'refurbished', 'Refurbished'
        USADO = 'usado', 'Used'

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='descuentos',
        help_text="Product that receives this discount"
    )
    condicion = models.CharField(
        max_length=20,
        choices=CondicionChoices.choices,
        help_text="Condition of units this discount applies to"
    )
    precio_descuento = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=False,
        help_text="Discounted sale price (COP)"
    )
    fecha_inicio = models.DateField(null=False, help_text="Date from which the discount is valid")
    fecha_fin = models.DateField(null=False, help_text="Date until which the discount is valid")

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        unique_together = [('producto', 'condicion')]

    def __str__(self):
        estado = "Active" if self.active else "Inactive"
        return f"{self.producto.nombre} ({self.condicion}) - ${self.precio_descuento} ({estado})"


#  removed - will be recreated for BajoPedido tracking only in Milestone 5
