"""
Punto de entrada único para el servicio Railway Cron.

Corre las dos tareas programadas de eBay de forma síncrona y en proceso:
no necesita broker Celery, ni worker, ni beat, ni Redis. Railway arranca
este comando según `cronSchedule`, corre, y el servicio se apaga.

    python manage.py correr_tareas_programadas                  # ambas tareas (manual)
    python manage.py correr_tareas_programadas --cron-frecuente # modo cron cada 8 min
    python manage.py correr_tareas_programadas --solo-notificador

Modos:
- Sin flags (uso manual / compatibilidad): corre precios Bajo Pedido + Deal Watcher.
- `--cron-frecuente` (lo usa el cron cada 8 min): el Deal Watcher corre en cada
  invocación; la reconciliación de precios solo en el primer tick de las horas
  UTC 0/12/18 (3x/día) para no agotar la cuota de eBay.
- `--solo-notificador`: corre únicamente el Deal Watcher.

Cada tarea está envuelta en su propio try/except para que el fallo de una
no impida la otra. Se schedulea desde `railway.cron.toml`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Horas UTC en las que corre la reconciliación de precios cuando el cron es
# frecuente. 00/12/18 UTC = 7pm/7am/1pm hora Colombia: la misma cadencia 3x/día
# que tenía el cron original (`0 0,12,18 * * *`).
HORAS_PRECIOS_UTC = (0, 12, 18)


class Command(BaseCommand):
    help = (
        "Corre las tareas programadas de eBay (precios Bajo Pedido + Deal Watcher). "
        "Con --cron-frecuente el notificador corre cada vez y los precios solo 3x/día."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--cron-frecuente",
            action="store_true",
            help=(
                "Modo cron cada 8 min: corre el Deal Watcher en cada invocación, "
                "pero la tarea de precios solo en las horas UTC 0/12/18 (3x/día), "
                "para no agotar la cuota de eBay."
            ),
        )
        parser.add_argument(
            "--solo-notificador",
            action="store_true",
            help="Corre únicamente el Deal Watcher; omite por completo la tarea de precios.",
        )

    def handle(self, *args, **options):
        self.stdout.write("== Tareas programadas: inicio ==")

        correr_precios = self._debe_correr_precios(options)

        # 1. Precios Bajo Pedido (eBay) ------------------------------------
        if correr_precios:
            try:
                from products.tasks import actualizar_precios_bajo_pedido
                # .apply() ejecuta el shared_task de forma síncrona, en este
                # proceso, sin tocar el broker. .get() devuelve el dict de
                # resultado y re-lanza cualquier excepción del task.
                result = actualizar_precios_bajo_pedido.apply().get()
                self.stdout.write(self.style.SUCCESS(f"Bajo Pedido: {result}"))
            except Exception as exc:  # noqa: BLE001 - una tarea no debe tumbar la otra
                logger.exception("Fallo en actualizar_precios_bajo_pedido")
                self.stderr.write(self.style.ERROR(f"Bajo Pedido FALLO: {exc}"))
        else:
            self.stdout.write("Bajo Pedido: omitido (fuera de ventana de reconciliación)")

        # 2. Deal Watcher --------------------------------------------------
        try:
            from deal_watcher.services import deal_checker, notifier as notifier_module
            summary = deal_checker.check_all_active(
                notifier=lambda product, snapshot, outcome: notifier_module.notify(
                    product, snapshot, outcome
                ),
                dry_run=False,
            )
            self.stdout.write(self.style.SUCCESS(
                f"Deal Watcher: total={summary.total} notified={summary.notified} "
                f"skipped={summary.skipped} errors={summary.errors}"
            ))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fallo en deal_watcher check")
            self.stderr.write(self.style.ERROR(f"Deal Watcher FALLO: {exc}"))

        self.stdout.write("== Tareas programadas: fin ==")

    def _debe_correr_precios(self, options) -> bool:
        """Decide si esta invocación corre la reconciliación de precios."""
        if options["solo_notificador"]:
            return False
        if not options["cron_frecuente"]:
            # Invocación normal/manual: corre ambas tareas como siempre.
            return True
        # Cron cada 8 min: solo en el primer tick (minuto < 8) de las horas
        # 0/12/18 UTC, para conservar la cadencia 3x/día y la cuota de eBay.
        ahora = datetime.now(dt_timezone.utc)
        return ahora.hour in HORAS_PRECIOS_UTC and ahora.minute < 8
