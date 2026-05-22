"""
Pacing del notificador (token-bucket / "presupuesto ganado").

El servicio Railway Cron dispara `correr_tareas_programadas --cron-frecuente`
cada 5 min, 24/7. Cada corrida es un proceso nuevo (sin estado en memoria), así
que el conteo de llamadas vive en BD (`UsoDiarioNotificador`).

En cada tick decidimos si correr el Deal Watcher repartiendo
`llamados_diarios_objetivo` de forma pareja SOLO dentro de la franja activa
(hora Colombia), sin pasarnos del presupuesto:

    ganado = presupuesto_efectivo * (minutos transcurridos en la franja / duración)
    corre si  (usado == 0)  o  (usado + N <= ganado)

donde N = nº de `MonitoredProduct` activos (máximo de llamadas por ciclo) y
`presupuesto_efectivo = objetivo - reserva_otros_llamados`. El conteo real se
hace por llamadas efectivas a eBay (`RunSummary.api_calls`), no por N.

Toda la lógica de tiempo usa `timezone.localtime()` → America/Bogota
(Colombia no tiene DST, así que la aritmética es estable). `now` es inyectable
para tests, igual que en `pause_service`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from deal_watcher.models import (
    ConfiguracionNotificador,
    MonitoredProduct,
    UsoDiarioNotificador,
)

MINUTOS_DIA = 24 * 60


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _parse_hhmm(value: str, fallback: time) -> time:
    try:
        h, m = value.split(':')
        return time(int(h), int(m))
    except (ValueError, AttributeError):
        return fallback


def get_config() -> ConfiguracionNotificador:
    """Devuelve el singleton (pk=1), creándolo con defaults de settings si falta."""
    config, _ = ConfiguracionNotificador.objects.get_or_create(
        pk=1,
        defaults={
            'hora_inicio_activa': _parse_hhmm(
                getattr(settings, 'NOTIFICADOR_VENTANA_INICIO_DEFAULT', '07:00'), time(7, 0)
            ),
            'hora_fin_activa': _parse_hhmm(
                getattr(settings, 'NOTIFICADOR_VENTANA_FIN_DEFAULT', '01:00'), time(1, 0)
            ),
            'llamados_diarios_objetivo': getattr(settings, 'NOTIFICADOR_OBJETIVO_DEFAULT', 5000),
            'reserva_otros_llamados': getattr(settings, 'NOTIFICADOR_RESERVA_DEFAULT', 200),
        },
    )
    return config


# ---------------------------------------------------------------------------
# Window math (Colombia local time)
# ---------------------------------------------------------------------------

def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def is_within_window(cfg: ConfiguracionNotificador, now_local: datetime) -> bool:
    t = now_local.time()
    ini, fin = cfg.hora_inicio_activa, cfg.hora_fin_activa
    if ini == fin:
        return True  # franja de 24 h
    if ini < fin:
        return ini <= t < fin  # mismo día
    return t >= ini or t < fin  # cruza medianoche


def window_duration_minutes(cfg: ConfiguracionNotificador) -> int:
    dur = (_minutes(cfg.hora_fin_activa) - _minutes(cfg.hora_inicio_activa)) % MINUTOS_DIA
    return dur if dur != 0 else MINUTOS_DIA  # ini == fin → 24 h


def period_start(cfg: ConfiguracionNotificador, now_local: datetime) -> datetime:
    """Inicio del período de presupuesto: la ocurrencia más reciente de
    `hora_inicio_activa` igual o anterior a `now_local`. Ancla el período a la
    franja (no a medianoche), de modo que un bloque que cruza medianoche
    conserva la misma clave hasta que termina."""
    ini = cfg.hora_inicio_activa
    candidate = now_local.replace(hour=ini.hour, minute=ini.minute, second=0, microsecond=0)
    if now_local.time() >= ini:
        return candidate
    return candidate - timedelta(days=1)


def period_key(cfg: ConfiguracionNotificador, now_local: datetime) -> date:
    return period_start(cfg, now_local).date()


def effective_budget(cfg: ConfiguracionNotificador) -> int:
    return max(0, cfg.llamados_diarios_objetivo - cfg.reserva_otros_llamados)


def earned_calls(cfg: ConfiguracionNotificador, now_local: datetime) -> float:
    """Llamadas "ganadas" hasta ahora: proporción del presupuesto efectivo según
    el tiempo transcurrido dentro de la franja."""
    budget = effective_budget(cfg)
    if budget <= 0:
        return 0.0
    duration = window_duration_minutes(cfg)
    elapsed = (now_local - period_start(cfg, now_local)).total_seconds() / 60.0
    frac = min(max(elapsed / duration, 0.0), 1.0)
    return budget * frac


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

@dataclass
class PacingDecision:
    should_run: bool
    reason: str
    n_products: int = 0
    earned: float = 0.0
    used: int = 0
    period: Optional[date] = None


def _active_products_count() -> int:
    return MonitoredProduct.objects.filter(active=True).count()


def should_run_now(
    cfg: Optional[ConfiguracionNotificador] = None,
    now: Optional[datetime] = None,
) -> PacingDecision:
    cfg = cfg or get_config()
    now = now or timezone.now()
    now_local = timezone.localtime(now)

    if not cfg.active:
        return PacingDecision(False, 'disabled')
    if not is_within_window(cfg, now_local):
        return PacingDecision(False, 'outside_window')

    n = _active_products_count()
    if n == 0:
        return PacingDecision(False, 'no_products')

    pk_day = period_key(cfg, now_local)
    uso, _ = UsoDiarioNotificador.objects.get_or_create(dia=pk_day)
    earned = earned_calls(cfg, now_local)

    # Primer ciclo del período corre siempre (garantiza una pasada temprana);
    # luego sólo si lo que llevamos usado + el costo del ciclo cabe en lo ganado.
    if uso.llamados_usados == 0 or (uso.llamados_usados + n) <= earned:
        return PacingDecision(True, 'ok', n, earned, uso.llamados_usados, pk_day)
    return PacingDecision(False, 'budget_exhausted', n, earned, uso.llamados_usados, pk_day)


def record_usage(period: date, api_calls: int, now: Optional[datetime] = None) -> None:
    """Suma las llamadas reales del ciclo y marca la corrida. Atómico por si un
    `run-now` manual se solapa con el cron."""
    now = now or timezone.now()
    with transaction.atomic():
        UsoDiarioNotificador.objects.get_or_create(dia=period)
        UsoDiarioNotificador.objects.filter(dia=period).update(
            llamados_usados=F('llamados_usados') + api_calls,
            ciclos_ejecutados=F('ciclos_ejecutados') + 1,
            ultima_ejecucion_at=now,
        )


# ---------------------------------------------------------------------------
# Status snapshot (para la página admin)
# ---------------------------------------------------------------------------

def get_status(
    cfg: Optional[ConfiguracionNotificador] = None,
    now: Optional[datetime] = None,
) -> dict:
    cfg = cfg or get_config()
    now = now or timezone.now()
    now_local = timezone.localtime(now)

    n = _active_products_count()
    budget = effective_budget(cfg)
    duration = window_duration_minutes(cfg)
    within = is_within_window(cfg, now_local)
    pk_day = period_key(cfg, now_local)

    uso = UsoDiarioNotificador.objects.filter(dia=pk_day).first()
    used = uso.llamados_usados if uso else 0
    cycles = uso.ciclos_ejecutados if uso else 0
    last_run = uso.ultima_ejecucion_at if uso else None

    # Cadencia teórica = duración / ciclos posibles = duración * N / presupuesto.
    cadencia_estimada = None
    cadencia_efectiva = None
    if n > 0 and budget > 0:
        cadencia_estimada = round(duration * n / budget, 1)
        cadencia_efectiva = max(5.0, cadencia_estimada)  # piso de Railway Cron = 5 min

    return {
        'enabled': cfg.active,
        'within_window': within,
        'period': pk_day,
        'window_label': f"{cfg.hora_inicio_activa:%H:%M}–{cfg.hora_fin_activa:%H:%M}",
        'objetivo': cfg.llamados_diarios_objetivo,
        'reserva': cfg.reserva_otros_llamados,
        'effective_budget': budget,
        'earned': round(earned_calls(cfg, now_local), 1),
        'used': used,
        'n_products': n,
        'cycles_today': cycles,
        'last_run_at': last_run,
        'cadencia_estimada_min': cadencia_estimada,
        'cadencia_efectiva_min': cadencia_efectiva,
    }
