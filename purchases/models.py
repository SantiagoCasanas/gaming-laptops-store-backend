from django.db import models
from django.conf import settings
from core.models import BaseModel
from products.models import UnidadProducto, Proveedor
from sales.models import Cliente


class OrdenCompra(BaseModel):
    """
    Purchase order for a specific unit.
    Can represent either an external purchase or a product received as trade-in.
    Automatically creates a UnidadProducto when the order is created.
    """
    class TipoChoices(models.TextChoices):
        COMPRA_EXTERNA = 'compra_externa', 'External Purchase'
        CANJE_CLIENTE = 'canje_cliente', 'Trade-in from Client'

    class EstadoLogisticoChoices(models.TextChoices):
        VIAJANDO = 'viajando', 'In Transit'
        EN_OFICINA_IMPORTADORA = 'en_oficina_importadora', 'At Importer Office'
        EN_OFICINA = 'en_oficina', 'In Store'

    producto = models.ForeignKey(
        'products.Producto',
        on_delete=models.PROTECT,
        related_name='ordenes_compra',
        null=True,
        blank=True,
        help_text="Product being purchased"
    )
    condicion = models.CharField(
        max_length=20,
        choices=[
            ('nuevo', 'New'),
            ('open_box', 'Open Box'),
            ('refurbished', 'Refurbished'),
            ('usado', 'Used')
        ],
        default='nuevo',
        help_text="Physical condition of the unit being created"
    )
    serial_generado = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Serial number for the unit (auto-generated if not provided)"
    )
    unidad_producto = models.OneToOneField(
        UnidadProducto,
        on_delete=models.PROTECT,
        related_name='orden_compra',
        null=True,
        blank=True,
        help_text="Specific unit created for this purchase order (auto-created on save)"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoChoices.choices,
        default=TipoChoices.COMPRA_EXTERNA,
        null=False,
        help_text="Type of purchase: external or trade-in"
    )
    estado_logistico = models.CharField(
        max_length=30,
        choices=EstadoLogisticoChoices.choices,
        default=EstadoLogisticoChoices.VIAJANDO,
        null=False,
        help_text="Logistic status of the purchase"
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        related_name='ordenes_compra',
        null=True,
        blank=True,
        help_text="Supplier (used for external purchases)"
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        related_name='ordenes_compra',
        null=True,
        blank=True,
        help_text="Customer (used for trade-in purchases)"
    )
    numero_orden = models.CharField(
        max_length=100,
        null=False,
        help_text="Order number from supplier or internal reference"
    )
    numero_tracking = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Tracking number for shipment (optional)"
    )
    costo_compra = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=False,
        help_text="Purchase cost (typically in USD)"
    )
    precio_venta = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Selling price for created unit; if blank, auto-calculated via formula"
    )
    costo_importacion = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Import costs if applicable (optional)"
    )
    impuesto_importacion = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=False,
        default=0,
        editable=False,
        help_text="Auto-calculated as 2% of costo_compra"
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name='ordenes_compra_modificadas',
        help_text="Last user who modified this purchase order"
    )

    class Meta:
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        ordering = ['-id']

    def save(self, *args, **kwargs):
        import uuid
        from decimal import Decimal
        from django.utils.timezone import now
        from core.services.trm_service import get_trm_for_date

        # Auto-calculate import tax as 2% of purchase cost
        self.impuesto_importacion = self.costo_compra * Decimal('0.02')

        super().save(*args, **kwargs)

        # Create or update the associated unit if no unit exists yet
        if not self.unidad_producto:
            # Generate serial if not provided
            serial = self.serial_generado
            if not serial:
                # Generate serial: ORD-{numero_orden}-{uuid[:8]}
                serial = f"ORD-{self.numero_orden}-{str(uuid.uuid4())[:8]}"

            # Determine initial estado_producto based on logistic status
            if self.estado_logistico == 'viajando':
                estado_producto = 'viajando'
            elif self.estado_logistico == 'en_oficina_importadora':
                estado_producto = 'por_comprar'
            else:  # en_oficina
                estado_producto = 'en_stock'

            # Calculate unit price
            if self.precio_venta:
                unit_price = self.precio_venta
            else:
                # Auto-calculate: ((costo_compra * 1.2) * TRM) + 50, rounded to nearest 90,000
                trm = get_trm_for_date(now().date())
                base_price = (self.costo_compra * Decimal('1.2') * trm) + Decimal('50')
                # Round to nearest 90,000
                unit_price = (base_price / Decimal('90000')).quantize(Decimal('1')) * Decimal('90000')

            # Create the unit
            unidad = UnidadProducto.objects.create(
                producto=self.producto,
                condicion=self.condicion,
                serial=serial,
                estado_venta='sin_vender',  # New units are not sold yet
                estado_producto=estado_producto,
                precio=unit_price,
                usuario_ultima_modificacion=self.usuario_ultima_modificacion
            )

            # Link the unit to this order
            self.unidad_producto = unidad
            self.serial_generado = serial
            super().save(update_fields=['unidad_producto', 'serial_generado'])

    def __str__(self):
        serial = self.unidad_producto.serial if self.unidad_producto else "pending"
        return f"PO {self.numero_orden} - {self.producto.nombre} ({self.condicion}) ({serial})"
