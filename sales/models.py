from django.db import models
from django.conf import settings
from core.models import BaseModel
from products.models import UnidadProducto


class Departamento(BaseModel):
    """Colombian department/region."""
    nombre = models.CharField(max_length=100, unique=True, null=False, help_text="Department name")
    codigo = models.CharField(max_length=5, blank=True, null=True, help_text="Optional department code")

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Ciudad(BaseModel):
    """Colombian city."""
    nombre = models.CharField(max_length=100, null=False, help_text="City name")
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='ciudades',
        null=False,
        help_text="Department this city belongs to"
    )

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"
        ordering = ['nombre']
        unique_together = [('nombre', 'departamento')]

    def __str__(self):
        return f"{self.nombre} ({self.departamento.nombre})"


class Cliente(BaseModel):
    """Customer record (not a system user)."""
    nombre_completo = models.CharField(max_length=200, null=False, help_text="Full name of the customer")
    cedula = models.CharField(max_length=50, unique=True, null=False, help_text="Unique identification document")
    celular = models.CharField(max_length=30, null=False, help_text="Phone number")
    correo = models.EmailField(unique=True, null=False, help_text="Email address")
    direccion = models.CharField(max_length=300, null=False, help_text="Physical address")
    ciudad = models.ForeignKey(
        Ciudad,
        on_delete=models.PROTECT,
        related_name='clientes',
        null=False,
        help_text="City where the customer is located"
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='clientes',
        null=False,
        help_text="Department where the customer is located"
    )

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ['nombre_completo']

    def __str__(self):
        return f"{self.nombre_completo} ({self.cedula})"


class SolicitudBajoPedido(BaseModel):
    """
    Represents a customer's individual request to purchase a product that is not currently in stock.
    Customer requests a specific product with condition, pays a deposit, and an OrdenCompra is created to source it.
    """
    class EstadoChoices(models.TextChoices):
        POR_COMPRAR = 'por_comprar', 'Pending Purchase'
        ACTIVA = 'activa', 'Active'
        COMPLETADA = 'completada', 'Completed'
        EXPIRADA = 'expirada', 'Expired'
        CANCELADA = 'cancelada', 'Cancelled'

    bajo_pedido = models.ForeignKey(
        'products.BajoPedido',
        on_delete=models.PROTECT,
        related_name='solicitudes_bajo_pedido',
        null=False,
        help_text="On-demand product listing the customer is requesting"
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='solicitudes_bajo_pedido',
        null=False,
        help_text="Customer requesting this product"
    )
    valor_abono = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=False,
        help_text="Initial payment/deposit from customer"
    )
    fecha_solicitud = models.DateField(
        auto_now_add=True,
        help_text="Date when customer requested the product"
    )
    fecha_maxima_compra = models.DateField(
        null=False,
        help_text="Deadline for the purchase to be completed"
    )
    orden_compra = models.OneToOneField(
        'purchases.OrdenCompra',
        on_delete=models.SET_NULL,
        related_name='solicitud_bajo_pedido',
        null=True,
        blank=True,
        help_text="Associated purchase order (set when order is created)"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.POR_COMPRAR,
        null=False,
        help_text="Current status of the request"
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name='solicitudes_bajo_pedido_modificadas',
        help_text="Last user who modified this record"
    )

    class Meta:
        verbose_name = "Customer Back Order Request"
        verbose_name_plural = "Customer Back Order Requests"
        ordering = ['-fecha_solicitud']
        unique_together = [('bajo_pedido', 'cliente')]

    def __str__(self):
        return f"Back order request: {self.cliente.nombre_completo} - {self.bajo_pedido}"


class Separacion(BaseModel):
    """
    Represents a hold/reservation on a specific unit that already exists in stock or in transit.
    Customer reserves a unit and pays a deposit.
    """
    class EstadoChoices(models.TextChoices):
        ACTIVA = 'activa', 'Active'
        EXPIRADA = 'expirada', 'Expired'
        CANCELADA = 'cancelada', 'Cancelled'
        COMPLETADA = 'completada', 'Completed'

    unidad_producto = models.ForeignKey(
        UnidadProducto,
        on_delete=models.PROTECT,
        related_name='separaciones',
        null=False,
        help_text="Specific unit being held"
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='separaciones',
        null=False,
        help_text="Customer holding this unit"
    )
    valor_abono = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=False,
        help_text="Deposit paid for the hold"
    )
    fecha_separacion = models.DateField(
        auto_now_add=True,
        help_text="Date when the hold was created"
    )
    fecha_maxima_compra = models.DateField(
        null=False,
        help_text="Deadline for customer to complete purchase"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.ACTIVA,
        null=False,
        help_text="Current status of the hold"
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name='separaciones_modificadas',
        help_text="Last user who modified this record"
    )

    class Meta:
        verbose_name = "Hold/Separation"
        verbose_name_plural = "Holds/Separations"
        ordering = ['-fecha_separacion']
        unique_together = [('unidad_producto', 'cliente')]

    def __str__(self):
        return f"Hold: {self.cliente.nombre_completo} - Unit {self.unidad_producto.serial}"


class Venta(BaseModel):
    """
    Sales transaction record.
    Can be linked to a previous separation or be standalone.
    """
    class EstadoEntregaChoices(models.TextChoices):
        POR_ENTREGAR = 'por_entregar', 'Pending Delivery'
        ENTREGADO = 'entregado', 'Delivered'

    class CanalChoices(models.TextChoices):
        TIENDA_FISICA = 'tienda_fisica', 'Tienda física'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        FACEBOOK = 'facebook', 'Facebook'
        INSTAGRAM = 'instagram', 'Instagram'
        OTRO = 'otro', 'Otro'

    class TipoEntregaChoices(models.TextChoices):
        LOCAL = 'local', 'Recogida en tienda'
        ENVIO = 'envio', 'Envío a domicilio'

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='ventas',
        null=False,
        help_text="Customer making the purchase"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time of the sale"
    )
    notas = models.TextField(
        blank=True,
        null=True,
        help_text="Optional notes about the sale"
    )
    separacion = models.ForeignKey(
        Separacion,
        on_delete=models.SET_NULL,
        related_name='ventas',
        null=True,
        blank=True,
        help_text="Associated hold/separation if this sale originated from one"
    )
    estado_entrega = models.CharField(
        max_length=20,
        choices=EstadoEntregaChoices.choices,
        default=EstadoEntregaChoices.POR_ENTREGAR,
        help_text="Delivery status of the sale"
    )
    fecha_entrega = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when the sale was delivered"
    )
    canal = models.CharField(
        max_length=20,
        choices=CanalChoices.choices,
        default=CanalChoices.TIENDA_FISICA,
        help_text="Channel through which the sale was closed"
    )
    tipo_entrega = models.CharField(
        max_length=10,
        choices=TipoEntregaChoices.choices,
        default=TipoEntregaChoices.LOCAL,
        help_text="Delivery modality agreed with the customer"
    )
    costo_envio_local = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Shipping cost inside Colombia absorbed by the business. 0 if local pickup."
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name='ventas_modificadas',
        help_text="Last user who modified this sale"
    )

    class Meta:
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        ordering = ['-fecha']

    def __str__(self):
        return f"Sale {self.id} - {self.cliente.nombre_completo} on {self.fecha.date()}"


class ItemVenta(BaseModel):
    """
    Line item in a sale.
    Stores a snapshot of the unit price at the time of sale.
    """
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='items',
        null=False,
        help_text="Sale this item belongs to"
    )
    unidad_producto = models.ForeignKey(
        UnidadProducto,
        on_delete=models.PROTECT,
        related_name='items_venta',
        null=False,
        help_text="Specific unit being sold"
    )
    precio = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=False,
        help_text="Price at the time of sale (snapshot)"
    )

    class Meta:
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"
        unique_together = [('venta', 'unidad_producto')]

    def __str__(self):
        return f"Item: {self.unidad_producto.serial} - ${self.precio}"


class Invoice(BaseModel):
    """
    Full invoice with document generation, email delivery, and file storage.
    Linked to a Cliente (FK), and optionally to a Venta or Separacion.
    Inherits active, created_at, updated_at from BaseModel.
    """
    CONCEPTO_CHOICES = [
        ('venta', 'Venta'),
        ('separacion', 'Separación'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('otro', 'Otro'),
    ]

    # Generated invoice ID: YYYYMMDD-{serial_item}
    bill_id = models.CharField(max_length=100, unique=True, editable=False)

    # Client FK (replaces denormalized client_* fields)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='invoices',
        null=False,
        help_text="Customer this invoice belongs to"
    )

    # Optional transaction links (mutually exclusive)
    venta = models.ForeignKey(
        Venta,
        on_delete=models.SET_NULL,
        related_name='invoices',
        null=True,
        blank=True,
        help_text="Associated sale (optional)"
    )
    separacion = models.ForeignKey(
        Separacion,
        on_delete=models.SET_NULL,
        related_name='invoices',
        null=True,
        blank=True,
        help_text="Associated hold/separation (optional)"
    )

    # Sale data
    concepto = models.CharField(max_length=20, choices=CONCEPTO_CHOICES)
    item = models.CharField(max_length=100, blank=True)
    serial_item = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    due_date = models.DateField()

    # R2 / local file path
    file_path = models.CharField(max_length=500, blank=True, null=True)
    email_sent = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.bill_id:
            date_str = self.due_date.strftime('%Y%m%d')
            self.bill_id = f"{date_str}-{self.serial_item.upper().replace(' ', '')}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bill_id} - {self.cliente.nombre_completo}"

    class Meta:
        ordering = ['-id']
