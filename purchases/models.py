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
        help_text="Purchase cost in COP. Forms may accept the value in USD for convenience and convert before saving."
    )
    costo_importacion = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Import costs in COP (optional). Set in COP via the bulk import upload."
    )
    impuesto_importacion = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=False,
        default=0,
        editable=False,
        help_text="Calculated as porcentaje_impuesto% of costo_compra (in COP, same currency as costo_compra)"
    )
    fecha_compra = models.DateField(
        blank=True,
        null=True,
        help_text="Real transaction date (editable). Defaults to creation date if omitted."
    )
    fecha_estimada_llegada = models.DateField(
        blank=True,
        null=True,
        help_text="ETA: auto-computed as fecha_compra + 15 business days (Mon-Fri). Editable."
    )
    fecha_en_viaje = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when estado_logistico transitioned to 'viajando'."
    )
    fecha_en_oficina_importadora = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when estado_logistico transitioned to 'en_oficina_importadora'."
    )
    fecha_en_oficina = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when estado_logistico transitioned to 'en_oficina'."
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
        from core.services.business_days import add_business_days

        # Use percentage provided by serializer via _pct_impuesto; default 2%
        pct = getattr(self, '_pct_impuesto', Decimal('2'))
        self.impuesto_importacion = self.costo_compra * (pct / Decimal('100'))

        # Default fecha_compra to today on first save if not provided.
        today = now().date()
        if not self.fecha_compra:
            self.fecha_compra = today

        # Auto-compute ETA (fecha_compra + 15 business days) if not provided.
        if not self.fecha_estimada_llegada:
            self.fecha_estimada_llegada = add_business_days(self.fecha_compra, 15)

        # Populate transition timestamps idempotently for the current status.
        current_now = now()
        if self.estado_logistico == 'viajando' and not self.fecha_en_viaje:
            self.fecha_en_viaje = current_now
        elif self.estado_logistico == 'en_oficina_importadora' and not self.fecha_en_oficina_importadora:
            self.fecha_en_oficina_importadora = current_now
        elif self.estado_logistico == 'en_oficina' and not self.fecha_en_oficina:
            self.fecha_en_oficina = current_now

        super().save(*args, **kwargs)

        # If unit already exists, sync estado_producto when logistic status changes
        # Only if unit has a real serial (not auto-generated placeholder)
        if self.unidad_producto and self.estado_logistico != 'viajando':
            if not self.unidad_producto.serial.startswith('SIN-SERIAL-'):
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

            # Auto-calculate unit price. All inputs are now in COP — no TRM
            # conversion required. Apply the 20% margin and round to the
            # nearest 100k + 90k tail (e.g. 4_290_000, 4_390_000, ...).
            costo_importacion_cop = self.costo_importacion or Decimal('0')
            impuesto = self.costo_compra * (pct / Decimal('100'))
            total_cop = self.costo_compra + impuesto + costo_importacion_cop
            raw = total_cop * Decimal('1.2')
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
