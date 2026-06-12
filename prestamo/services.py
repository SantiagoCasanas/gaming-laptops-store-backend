"""
Capa de orquestación de la app `prestamo`.

Conecta el motor puro (`engine.py`) con la persistencia (`models.py`):
- Lee la configuración activa y los abonos, corre el motor y persiste los
  snapshots `PeriodoCalculado` + refresca el cache de `Tramo`.
- Arma el `resumen` (saldos actuales, próxima cuota, próximo 2%, mes en curso).
- Registra auditoría inmutable.

Todo el dinero viaja en Decimal; el redondeo a 2 decimales es solo de salida.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from . import engine
from .models import AuditLog, Configuracion, Movimiento, PeriodoCalculado, Tramo

# Campos monetarios de cada fila que persistimos redondeados.
_CAMPOS = (
    "saldo_inicial", "abono", "saldo_post_abono", "interes",
    "comision", "cuota", "abono_capital", "saldo_final",
)


def get_config():
    """Configuración activa, o None si aún no se ha sembrado."""
    return Configuracion.objects.filter(activa=True).order_by("-id").first()


def _abonos_para_motor(config):
    """Convierte los Movimientos de tipo abono en el insumo del motor:
    {'mes': int, 'tramo': 'amigo'|'dueno', 'monto': Decimal}."""
    abonos = []
    qs = Movimiento.objects.filter(tipo__in=Movimiento.TIPOS_ABONO)
    for mov in qs:
        mes = engine.resolver_mes(mov.fecha, config.fecha_primer_corte, config.dia_corte)
        mes = max(1, min(mes, config.plazo))
        abonos.append({"mes": mes, "tramo": mov.tramo, "monto": mov.monto})
    return abonos


def _redondear_fila(fila):
    """Redondea una fila del motor a 2 decimales (string) por tramo."""
    out = {"mes": fila["mes"]}
    for tramo in ("amigo", "dueno", "banco"):
        out[tramo] = {c: str(engine.redondear(fila[tramo][c])) for c in _CAMPOS}
    return out


def mes_en_curso(config, hoy=None):
    """Período (mes) en curso según la fecha de hoy y el día de corte."""
    hoy = hoy or timezone.localdate()
    mes = engine.resolver_mes(hoy, config.fecha_primer_corte, config.dia_corte)
    return max(1, min(mes, config.plazo))


@transaction.atomic
def recalcular(config=None):
    """Corre el motor desde cero y persiste PeriodoCalculado + cache de Tramo.

    El motor es determinista: recalcular siempre regenera la tabla completa a
    partir de la configuración y TODOS los abonos. Devuelve las filas crudas.
    """
    config = config or get_config()
    if config is None:
        return []

    abonos = _abonos_para_motor(config)
    filas = engine.proyectar(config.as_engine_config(), abonos)

    # Regenerar snapshots.
    PeriodoCalculado.objects.all().delete()
    PeriodoCalculado.objects.bulk_create(
        [PeriodoCalculado(mes=f["mes"], datos=_redondear_fila(f)) for f in filas]
    )

    # Refrescar cache de tramos con el período en curso.
    m = mes_en_curso(config)
    fila_actual = filas[m - 1]
    for nombre in (Tramo.AMIGO, Tramo.DUENO):
        Tramo.objects.update_or_create(
            nombre=nombre,
            defaults={
                "saldo_vigente": engine.redondear(fila_actual[nombre]["saldo_inicial"]),
                "cuota_vigente": engine.redondear(fila_actual[nombre]["cuota"]),
            },
        )
    return filas


def get_proyeccion():
    """Tabla mes a mes (redondeada) desde los snapshots; recalcula si faltan."""
    if not PeriodoCalculado.objects.exists():
        recalcular()
    return [p.datos for p in PeriodoCalculado.objects.all().order_by("mes")]


def get_resumen():
    """Resumen para el dashboard: saldos actuales, próxima cuota (amigo y
    dueño), próximo 2% estimado y mes en curso."""
    config = get_config()
    if config is None:
        return {"configurado": False}

    filas = engine.proyectar(config.as_engine_config(), _abonos_para_motor(config))
    m = mes_en_curso(config)
    actual = filas[m - 1]

    def r(x):
        return str(engine.redondear(x))

    # "Saldo actual" = saldo ya con los abonos del período en curso
    # descontados (saldo_post_abono). Si no hubo abono este período coincide
    # con el saldo de apertura; si lo hubo, lo refleja de inmediato.
    return {
        "configurado": True,
        "mes_en_curso": m,
        "plazo": config.plazo,
        "fecha_corte": config.dia_corte,
        "amigo": {
            "saldo_actual": r(actual["amigo"]["saldo_post_abono"]),
            "proxima_cuota": r(actual["amigo"]["cuota"]),
            "proximo_2pct": r(actual["amigo"]["comision"]),
        },
        "dueno": {
            "saldo_actual": r(actual["dueno"]["saldo_post_abono"]),
            "proxima_cuota": r(actual["dueno"]["cuota"]),
        },
        "banco": {
            "saldo_actual": r(actual["banco"]["saldo_post_abono"]),
            "cuota_total": r(actual["banco"]["cuota"]),
        },
    }


def _fecha_corte(config, mes):
    """Fecha del corte (día de corte) del período `mes`."""
    fpc = config.fecha_primer_corte
    total = (fpc.month - 1) + (mes - 1)
    anio = fpc.year + total // 12
    mes_cal = total % 12 + 1
    return date(anio, mes_cal, config.dia_corte)


def periodo_cobro_actual(config, hoy=None):
    """Período cuyo corte (día 11) es el más reciente a la fecha `hoy`.

    A diferencia de `mes_en_curso` (que mira el PRÓXIMO corte para ubicar
    abonos), esto devuelve el corte que ya ocurrió hoy o el último que pasó —
    es el período que se está pagando cuando se hace el "pago regular" del 11.
    """
    hoy = hoy or timezone.localdate()
    fpc = config.fecha_primer_corte
    meses = (hoy.year - fpc.year) * 12 + (hoy.month - fpc.month)
    periodo = meses + 1 if hoy.day >= config.dia_corte else meses
    return max(1, min(periodo, config.plazo))


def _items_pago_regular(config, mes):
    """Devuelve las líneas (tipo, tramo, monto) del pago regular del mes,
    omitiendo las de monto 0 (p.ej. el dueño aún no tiene cuota en el mes 1)."""
    filas = engine.proyectar(config.as_engine_config(), _abonos_para_motor(config))
    fila = filas[mes - 1]
    candidatos = [
        (Movimiento.CUOTA_AMIGO, "amigo", engine.redondear(fila["amigo"]["cuota"])),
        (Movimiento.CUOTA_DUENO, "dueno", engine.redondear(fila["dueno"]["cuota"])),
        (Movimiento.COMISION, "amigo", engine.redondear(fila["amigo"]["comision"])),
    ]
    return [(t, tr, m) for (t, tr, m) in candidatos if m > Decimal("0")]


def preview_pago_regular(config=None, mes=None, hoy=None):
    """Resumen de lo que se registraría con el pago regular del período `mes`
    (por defecto, el corte vigente). No persiste nada."""
    config = config or get_config()
    if config is None:
        return {"configurado": False}
    if mes is None:
        mes = periodo_cobro_actual(config, hoy)
    mes = max(1, min(int(mes), config.plazo))

    items = _items_pago_regular(config, mes)
    fecha = _fecha_corte(config, mes)
    montos = {tipo: str(monto) for tipo, _tramo, monto in items}
    total = sum((monto for _t, _tr, monto in items), Decimal("0"))
    ya_pagado = Movimiento.objects.filter(
        tipo=Movimiento.CUOTA_AMIGO, fecha=fecha
    ).exists()

    return {
        "configurado": True,
        "mes": mes,
        "fecha": fecha.isoformat(),
        "ya_pagado": ya_pagado,
        "cuota_amigo": montos.get(Movimiento.CUOTA_AMIGO, "0"),
        "cuota_dueno": montos.get(Movimiento.CUOTA_DUENO, "0"),
        "comision_2pct": montos.get(Movimiento.COMISION, "0"),
        "total": str(total),
    }


@transaction.atomic
def registrar_pago_regular(usuario, mes=None, comprobante_url=""):
    """Registra de una sola vez las 3 líneas del corte del día 11 del período
    `mes` (cuota amigo, cuota dueño y 2% del amigo). Idempotente por período:
    si ya existe la cuota del amigo en esa fecha, lanza ValueError. Si se pasa
    `comprobante_url`, se adjunta a las 3 líneas."""
    config = get_config()
    if config is None:
        raise ValueError("No hay configuración sembrada.")
    if mes is None:
        mes = periodo_cobro_actual(config)
    mes = max(1, min(int(mes), config.plazo))

    fecha = _fecha_corte(config, mes)
    if Movimiento.objects.filter(tipo=Movimiento.CUOTA_AMIGO, fecha=fecha).exists():
        raise ValueError(f"El pago regular del mes {mes} ya fue registrado.")

    creados = []
    autor = usuario if (usuario and usuario.is_authenticated) else None
    for tipo, tramo, monto in _items_pago_regular(config, mes):
        mov = Movimiento.objects.create(
            tipo=tipo, tramo=tramo, monto=monto, fecha=fecha,
            autor=autor, nota=f"Pago regular mes {mes}",
            comprobante_url=comprobante_url or "",
        )
        registrar_auditoria(usuario, AuditLog.CREAR, mov,
                            antes=None, despues=movimiento_snapshot(mov))
        creados.append(mov)

    recalcular(config)
    return {"mes": mes, "fecha": fecha.isoformat(), "movimientos": creados}


def registrar_auditoria(usuario, accion, instancia, antes=None, despues=None):
    """Escribe un registro inmutable de auditoría."""
    AuditLog.objects.create(
        usuario=usuario if (usuario and usuario.is_authenticated) else None,
        accion=accion,
        modelo=instancia.__class__.__name__,
        objeto_id=str(getattr(instancia, "pk", "") or ""),
        valores_antes=antes,
        valores_despues=despues,
    )


def movimiento_snapshot(mov):
    """Representación serializable de un Movimiento para la auditoría."""
    return {
        "tipo": mov.tipo,
        "tramo": mov.tramo,
        "monto": str(mov.monto),
        "fecha": mov.fecha.isoformat() if mov.fecha else None,
        "nota": mov.nota,
        "comprobante_url": mov.comprobante_url,
    }
