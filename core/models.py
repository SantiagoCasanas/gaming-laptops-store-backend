from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model that provides an active field.
    This model should be inherited by other models that need active/inactive status.
    Does not create a table in the database.
    """
    active = models.BooleanField(
        verbose_name='active',
        default=True,
        help_text='Indicates whether this record is active or not'
    )

    class Meta:
        abstract = True


class TRMHistory(models.Model):
    """
    Tracks the USD to COP exchange rate (TRM) over time.
    Used for automated price calculations for eBay variants.
    """
    fecha = models.DateField(
        unique=True,
        help_text="Date of the exchange rate"
    )
    valor_cop = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="USD to COP exchange rate value"
    )
    fuente = models.CharField(
        max_length=100,
        default='superfinanciera',
        help_text="Source of the exchange rate (e.g. superfinanciera, banco_central)"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created"
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = "TRM History"
        verbose_name_plural = "TRM Histories"

    def __str__(self):
        return f"TRM {self.fecha}: {self.valor_cop}"
