from django.db import models
from django.conf import settings
from core.models import BaseModel
from products.models import UnidadProducto, Proveedor


class OrdenCompra(BaseModel):
    """
    Purchase order for a specific unit.
    Automatically creates a UnidadProducto when the order is created.
    """
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
            ('nuevo', 'Nuevo'),
            ('open_box', 'Open Box'),
            ('refurbished', 'Reacondicionado'),
            ('usado', 'Usado')
        ],
        default='nuevo',
        help_text="Physical condition of the unit being created"
    )
    unidad_producto = models.OneToOneField(
        UnidadProducto,
        on_delete=models.PROTECT,
        related_name='orden_compra',
        null=True,
        blank=True,
        help_text="Specific unit created for this purchase order (auto-created on save)"
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
        help_text="Supplier for this purchase"
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

        # If unit already exists, sync estado_producto when logistic status changes
        if self.unidad_producto and self.estado_logistico != 'viajando':
            self.unidad_producto.estado_producto = 'en_stock'
            self.unidad_producto.save(update_fields=['estado_producto'])

        # Create the associated unit if none exists yet
        if not self.unidad_producto:
            serial = f"SIN-SERIAL-{self.numero_orden}-{str(uuid.uuid4())[:6].upper()}"

            # Determine initial estado_producto based on logistic status
            if self.estado_logistico == 'viajando':
                estado_producto = 'viajando'
            elif self.estado_logistico == 'en_oficina_importadora':
                estado_producto = 'por_comprar'
            else:  # en_oficina
                estado_producto = 'en_stock'

            # Auto-calculate unit price: round((costo_total * 1.2 * TRM - 90000) / 100000) * 100000 + 90000
            trm = get_trm_for_date(now().date())
            costo_importacion = self.costo_importacion or Decimal('0')
            impuesto = self.costo_compra * Decimal('0.02')
            total_usd = self.costo_compra + costo_importacion + impuesto
            raw = total_usd * Decimal('1.2') * trm.valor_cop
            unit_price = (round((raw - Decimal('90000')) / Decimal('100000'))) * Decimal('100000') + Decimal('90000')

            # Create the unit
            unidad = UnidadProducto.objects.create(
                producto=self.producto,
                condicion=self.condicion,
                serial=serial,
                estado_venta='sin_vender',
                estado_producto=estado_producto,
                precio=unit_price,
                usuario_ultima_modificacion=self.usuario_ultima_modificacion
            )

            self.unidad_producto = unidad
            super().save(update_fields=['unidad_producto'])

    def __str__(self):
        serial = self.unidad_producto.serial if self.unidad_producto else "pending"
        return f"PO {self.numero_orden} - {self.producto.nombre if self.producto else 'N/A'} ({self.condicion}) ({serial})"
