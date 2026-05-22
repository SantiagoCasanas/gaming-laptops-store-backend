"""Tests del pacing del notificador (scheduler_service).

`now` se inyecta como datetime aware en hora Colombia (America/Bogota, sin DST).
Las funciones puras (ventana, duración, ganado) operan sobre instancias en
memoria de ConfiguracionNotificador; should_run_now/record_usage tocan la BD.
"""
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from deal_watcher.models import ConfiguracionNotificador, UsoDiarioNotificador
from deal_watcher.services import scheduler_service as ss
from deal_watcher.tests.factories import MonitoredProductFactory


pytestmark = pytest.mark.django_db

BOG = ZoneInfo("America/Bogota")


def bog(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=BOG)


def _cfg(inicio=time(7, 0), fin=time(19, 0), objetivo=1000, reserva=0, active=True):
    """Instancia en memoria (sin guardar) — suficiente para el pacing."""
    return ConfiguracionNotificador(
        hora_inicio_activa=inicio,
        hora_fin_activa=fin,
        llamados_diarios_objetivo=objetivo,
        reserva_otros_llamados=reserva,
        active=active,
    )


# ---------------------------------------------------------------------------
# is_within_window
# ---------------------------------------------------------------------------

def test_within_window_same_day():
    cfg = _cfg(time(7, 0), time(18, 0))
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 9, 0)) is True
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 7, 0)) is True   # inclusivo
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 18, 0)) is False  # exclusivo
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 6, 59)) is False
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 19, 0)) is False


def test_within_window_crosses_midnight():
    cfg = _cfg(time(7, 0), time(1, 0))
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 23, 30)) is True
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 0, 30)) is True
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 3, 0)) is False
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 6, 59)) is False


def test_within_window_24h():
    cfg = _cfg(time(0, 0), time(0, 0))
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 3, 0)) is True
    assert ss.is_within_window(cfg, bog(2026, 5, 21, 23, 59)) is True


# ---------------------------------------------------------------------------
# duración / período / presupuesto / ganado
# ---------------------------------------------------------------------------

def test_window_duration_minutes():
    assert ss.window_duration_minutes(_cfg(time(7, 0), time(19, 0))) == 720
    assert ss.window_duration_minutes(_cfg(time(7, 0), time(1, 0))) == 1080
    assert ss.window_duration_minutes(_cfg(time(0, 0), time(0, 0))) == 1440


def test_period_anchored_to_start_not_midnight():
    cfg = _cfg(time(7, 0), time(1, 0))
    # 00:30 sigue dentro del bloque que empezó AYER 07:00
    ps = ss.period_start(cfg, bog(2026, 5, 21, 0, 30))
    assert ps.date() == date(2026, 5, 20)
    assert ps.hour == 7
    assert ss.period_key(cfg, bog(2026, 5, 21, 0, 30)) == date(2026, 5, 20)
    # 09:00 → bloque de hoy
    assert ss.period_key(cfg, bog(2026, 5, 21, 9, 0)) == date(2026, 5, 21)


def test_effective_budget_subtracts_reserve():
    assert ss.effective_budget(_cfg(objetivo=5000, reserva=200)) == 4800
    assert ss.effective_budget(_cfg(objetivo=100, reserva=200)) == 0  # nunca negativo


def test_earned_calls_proportional_and_clamped():
    cfg = _cfg(time(7, 0), time(19, 0), objetivo=1000, reserva=0)  # 12h
    # 13:00 = mitad → ~50%
    assert abs(ss.earned_calls(cfg, bog(2026, 5, 21, 13, 0)) - 500) < 1
    # justo antes del fin → casi todo, sin pasarse
    e = ss.earned_calls(cfg, bog(2026, 5, 21, 18, 59))
    assert 990 <= e <= 1000


def test_earned_zero_when_no_budget():
    cfg = _cfg(objetivo=100, reserva=200)  # efectivo 0
    assert ss.earned_calls(cfg, bog(2026, 5, 21, 13, 0)) == 0.0


# ---------------------------------------------------------------------------
# should_run_now
# ---------------------------------------------------------------------------

def test_should_run_skips_when_disabled():
    cfg = _cfg(active=False)
    MonitoredProductFactory()
    d = ss.should_run_now(cfg=cfg, now=bog(2026, 5, 21, 9, 0))
    assert d.should_run is False and d.reason == "disabled"


def test_should_run_skips_outside_window():
    cfg = _cfg(time(7, 0), time(19, 0))
    MonitoredProductFactory()
    d = ss.should_run_now(cfg=cfg, now=bog(2026, 5, 21, 3, 0))
    assert d.should_run is False and d.reason == "outside_window"


def test_should_run_skips_when_no_products():
    cfg = _cfg(time(7, 0), time(19, 0))
    d = ss.should_run_now(cfg=cfg, now=bog(2026, 5, 21, 9, 0))
    assert d.should_run is False and d.reason == "no_products"


def test_should_run_first_cycle_runs_immediately():
    cfg = _cfg(time(7, 0), time(19, 0), objetivo=1000, reserva=0)
    MonitoredProductFactory()
    d = ss.should_run_now(cfg=cfg, now=bog(2026, 5, 21, 7, 0))
    assert d.should_run is True and d.reason == "ok"


def test_should_run_paces_over_a_day_without_exceeding_budget():
    # Ventana 07:00–19:00 (720 min), presupuesto efectivo 1000, N=10.
    cfg = _cfg(time(7, 0), time(19, 0), objetivo=1000, reserva=0)
    for _ in range(10):
        MonitoredProductFactory()

    runs = 0
    t = bog(2026, 5, 21, 7, 0)
    end = bog(2026, 5, 21, 19, 0)
    while t < end:
        d = ss.should_run_now(cfg=cfg, now=t)
        if d.should_run:
            ss.record_usage(d.period, d.n_products, now=t)  # cuenta N (peor caso)
            runs += 1
        t += timedelta(minutes=5)

    uso = UsoDiarioNotificador.objects.get(dia=date(2026, 5, 21))
    assert runs > 0
    # Nunca excede el presupuesto efectivo (± un ciclo) y lo consume casi entero.
    assert uso.llamados_usados <= 1000 + 10
    assert uso.llamados_usados >= 900
    assert uso.ciclos_ejecutados == runs


def test_record_usage_accumulates():
    dia = date(2026, 5, 21)
    ss.record_usage(dia, 5, now=bog(2026, 5, 21, 8, 0))
    uso = UsoDiarioNotificador.objects.get(dia=dia)
    assert uso.llamados_usados == 5
    assert uso.ciclos_ejecutados == 1
    assert uso.ultima_ejecucion_at is not None

    ss.record_usage(dia, 3, now=bog(2026, 5, 21, 8, 5))
    uso.refresh_from_db()
    assert uso.llamados_usados == 8
    assert uso.ciclos_ejecutados == 2


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

def test_get_status_shape():
    cfg = _cfg(time(7, 0), time(19, 0), objetivo=1000, reserva=0)
    MonitoredProductFactory()
    status = ss.get_status(cfg=cfg, now=bog(2026, 5, 21, 13, 0))
    assert status["within_window"] is True
    assert status["effective_budget"] == 1000
    assert status["n_products"] == 1
    assert status["window_label"] == "07:00–19:00"
    assert "cadencia_efectiva_min" in status
