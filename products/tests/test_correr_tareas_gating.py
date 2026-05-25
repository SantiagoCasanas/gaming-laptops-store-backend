"""
CASE 7 — Gating of the daily Bajo Pedido sync inside
`correr_tareas_programadas.Command._debe_correr_sync(options)`.

Rules (with `HORA_SYNC_BAJO_PEDIDO_UTC` = 11 by default):
- `--cron-frecuente`, hour == HORA and minute < 5  → True  (first tick of the day)
- `--cron-frecuente`, same hour, minute >= 5        → False
- `--cron-frecuente`, other hour                     → False
- `--solo-notificador`                               → False (always)
- manual (no flags)                                  → True

The command reads `datetime.now(timezone.utc)` from its own module, so we patch
`...correr_tareas_programadas.datetime`. No DB needed.
"""
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import override_settings

from products.management.commands.correr_tareas_programadas import Command

_MODULE = 'products.management.commands.correr_tareas_programadas'


def _options(*, cron_frecuente=False, solo_notificador=False):
    return {'cron_frecuente': cron_frecuente, 'solo_notificador': solo_notificador}


def _run_with_now(options, fake_now):
    with patch(f'{_MODULE}.datetime') as m:
        m.now.return_value = fake_now
        return Command()._debe_correr_sync(options)


@override_settings(HORA_SYNC_BAJO_PEDIDO_UTC=11)
def test_cron_hora_correcta_minuto_menor_5_true():
    now = datetime(2026, 5, 22, 11, 2, 0, tzinfo=dt_timezone.utc)
    assert _run_with_now(_options(cron_frecuente=True), now) is True


@override_settings(HORA_SYNC_BAJO_PEDIDO_UTC=11)
def test_cron_hora_correcta_minuto_5_o_mas_false():
    now = datetime(2026, 5, 22, 11, 7, 0, tzinfo=dt_timezone.utc)
    assert _run_with_now(_options(cron_frecuente=True), now) is False


@override_settings(HORA_SYNC_BAJO_PEDIDO_UTC=11)
def test_cron_otra_hora_false():
    now = datetime(2026, 5, 22, 12, 2, 0, tzinfo=dt_timezone.utc)
    assert _run_with_now(_options(cron_frecuente=True), now) is False


@override_settings(HORA_SYNC_BAJO_PEDIDO_UTC=11)
def test_solo_notificador_siempre_false():
    # Even at the exact sync window, --solo-notificador wins.
    now = datetime(2026, 5, 22, 11, 1, 0, tzinfo=dt_timezone.utc)
    assert _run_with_now(
        _options(cron_frecuente=True, solo_notificador=True), now
    ) is False


@override_settings(HORA_SYNC_BAJO_PEDIDO_UTC=11)
def test_manual_sin_flags_true():
    # Manual run ignores the clock entirely.
    now = datetime(2026, 5, 22, 23, 59, 0, tzinfo=dt_timezone.utc)
    assert _run_with_now(_options(), now) is True
