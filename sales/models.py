from django.db import models


class Invoice(models.Model):
    CONCEPTO_CHOICES = [
        ('venta', 'Venta'),
        ('separacion', 'Separación'),
    ]
    ITEM_CHOICES = [
        ('laptop', 'Laptop'),
        ('tarjeta_grafica', 'Tarjeta Gráfica'),
        ('hardware', 'Hardware'),
        ('pc_mesa', 'PC de Mesa'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('otro', 'Otro'),
    ]

    # Generated invoice ID: YYYYMMDD-{serial_item}
    bill_id = models.CharField(max_length=100, unique=True, editable=False)

    # Client data
    client_name = models.CharField(max_length=200)
    client_document = models.CharField(max_length=50)
    client_phone = models.CharField(max_length=30)
    client_address = models.CharField(max_length=300)
    client_email = models.EmailField()

    # Sale data
    concepto = models.CharField(max_length=20, choices=CONCEPTO_CHOICES)
    item = models.CharField(max_length=30, choices=ITEM_CHOICES)
    serial_item = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    due_date = models.DateField()

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # R2 file path
    file_path = models.CharField(max_length=500, blank=True, null=True)
    email_sent = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.bill_id:
            date_str = self.due_date.strftime('%Y%m%d')
            self.bill_id = f"{date_str}-{self.serial_item.upper().replace(' ', '')}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bill_id} - {self.client_name}"

    class Meta:
        ordering = ['-created_at']
