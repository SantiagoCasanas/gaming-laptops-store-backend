"""
Modelos de la app `prestamo` — app nueva y aislada dentro del proyecto.
No toca ninguna otra app. Prefijo de URL: /api/prestamo/.

El dinero se guarda con DecimalField (nunca float). Los cálculos los hace el
motor puro (`engine.py`); estos modelos almacenan la configuración, los
movimientos (insumo + bitácora) y los snapshots regenerables del motor.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models


class Configuracion(models.Model):
    """Parámetros del préstamo. Singleton lógico (se usa el registro `activa`).

    Sembrada con los valores reales (prestamo.md §1). Editable.
    """

    capital = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("45000000"),
        help_text="Capital inicial del banco (mes 0).",
    )
    ea = models.DecimalField(
        max_digits=8, decimal_places=6, default=Decimal("0.1996"),
        help_text="Tasa Efectiva Anual (p.ej. 0.1996).",
    )
    i_m = models.DecimalField(
        max_digits=14, decimal_places=12, default=Decimal("0.015281263150"),
        help_text="Tasa mensual equivalente = (1+EA)^(1/12)-1. Derivable de EA.",
    )
    plazo = models.PositiveIntegerField(
        default=48, help_text="Número total de cuotas (meses).",
    )
    dia_corte = models.PositiveIntegerField(
        default=11, help_text="Día de corte de cada mes (cobro del 2% y cuota).",
    )
    mes_renegociacion = models.PositiveIntegerField(
        default=2, help_text="Mes en que el saldo se parte en amigo/dueño.",
    )
    comision_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0.0200"),
        help_text="Comisión del amigo por corte (p.ej. 0.02 = 2%).",
    )
    saldo_dueno = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("5000000"),
        help_text="Saldo que conserva el dueño tras renegociar.",
    )
    saldo_amigo_reneg = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("40000000"),
        help_text="Saldo nominal del amigo al renegociar (informativo).",
    )
    fecha_primer_corte = models.DateField(
        help_text="Fecha del corte del mes 1 (día de corte del primer período).",
    )
    activa = models.BooleanField(
        default=True, help_text="Configuración vigente que usa el motor.",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "prestamo_configuracion"
        verbose_name = "Configuración de préstamo"
        verbose_name_plural = "Configuraciones de préstamo"

    def __str__(self):
        return f"Config préstamo (capital={self.capital}, EA={self.ea})"

    def as_engine_config(self):
        """Devuelve el dict que consume `engine.proyectar`."""
        return {
            "capital": self.capital,
            "ea": self.ea,
            "i_m": self.i_m,
            "plazo": self.plazo,
            "mes_renegociacion": self.mes_renegociacion,
            "saldo_dueno": self.saldo_dueno,
            "comision_pct": self.comision_pct,
        }


class Tramo(models.Model):
    """Cada deuda independiente: 'amigo' y 'dueno'. Saldo y cuota vigentes
    (cache derivada del motor; se refresca en cada recálculo)."""

    AMIGO = "amigo"
    DUENO = "dueno"
    TRAMO_CHOICES = [(AMIGO, "Amigo"), (DUENO, "Dueño")]

    nombre = models.CharField(max_length=10, choices=TRAMO_CHOICES, unique=True)
    saldo_vigente = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0"),
    )
    cuota_vigente = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0"),
    )
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "prestamo_tramo"
        verbose_name = "Tramo"
        verbose_name_plural = "Tramos"

    def __str__(self):
        return f"Tramo {self.nombre} (saldo={self.saldo_vigente})"


class Movimiento(models.Model):
    """Movimiento del préstamo. Los abonos son el insumo que perturba al motor;
    las cuotas y comisiones son bitácora de lo realmente pagado."""

    CUOTA_AMIGO = "cuota_amigo"
    CUOTA_DUENO = "cuota_dueno"
    ABONO_AMIGO = "abono_amigo"
    ABONO_DUENO = "abono_dueno"
    COMISION = "comision_2pct"
    TIPO_CHOICES = [
        (CUOTA_AMIGO, "Cuota amigo"),
        (CUOTA_DUENO, "Cuota dueño"),
        (ABONO_AMIGO, "Abono amigo"),
        (ABONO_DUENO, "Abono dueño"),
        (COMISION, "Comisión 2%"),
    ]
    # Tipos que el motor toma como abono a capital.
    TIPOS_ABONO = {ABONO_AMIGO, ABONO_DUENO}

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    tramo = models.CharField(max_length=10, choices=Tramo.TRAMO_CHOICES)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    fecha = models.DateField(help_text="Fecha del movimiento.")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="movimientos_prestamo",
    )
    nota = models.TextField(blank=True, default="")
    comprobante_url = models.URLField(max_length=1024, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "prestamo_movimiento"
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        ordering = ["-fecha", "-created_at"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.monto} ({self.fecha})"

    @property
    def es_abono(self):
        return self.tipo in self.TIPOS_ABONO


class PeriodoCalculado(models.Model):
    """Snapshot mes a mes producido por el motor. Regenerable: se borra y
    recrea en cada recálculo. `datos` guarda los valores ya redondeados a 2
    decimales (como string) para amigo/dueño/banco."""

    mes = models.PositiveIntegerField(unique=True)
    datos = models.JSONField(
        help_text="{'amigo': {...}, 'dueno': {...}, 'banco': {...}} redondeado.",
    )
    generado_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "prestamo_periodo_calculado"
        verbose_name = "Período calculado"
        verbose_name_plural = "Períodos calculados"
        ordering = ["mes"]

    def __str__(self):
        return f"Período mes {self.mes}"


class AuditLog(models.Model):
    """Bitácora inmutable de cambios. Se escribe en cada crear/editar/borrar de
    Movimiento (y de Configuración). No se edita ni se borra vía API."""

    CREAR = "crear"
    EDITAR = "editar"
    BORRAR = "borrar"
    ACCION_CHOICES = [(CREAR, "Crear"), (EDITAR, "Editar"), (BORRAR, "Borrar")]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="auditoria_prestamo",
    )
    accion = models.CharField(max_length=10, choices=ACCION_CHOICES)
    modelo = models.CharField(max_length=50)
    objeto_id = models.CharField(max_length=50, blank=True, default="")
    valores_antes = models.JSONField(null=True, blank=True)
    valores_despues = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prestamo_audit_log"
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.accion} {self.modelo}#{self.objeto_id} @ {self.timestamp}"
