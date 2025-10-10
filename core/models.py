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
