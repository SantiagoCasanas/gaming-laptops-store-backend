"""
Punto de entrada único para el servicio Railway Cron.

Corre las dos tareas programadas de eBay de forma síncrona y en proceso:
no necesita broker Celery, ni worker, ni beat, ni Redis. Railway arranca
este comando según `cronSchedule`, corre, y el servicio se apaga.

    python manage.py correr_tareas_programadas

Cada tarea está envuelta en su propio try/except para que el fallo de una
no impida la otra. Se schedulea desde `railway.cron.toml`.
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Corre las tareas programadas (precios Bajo Pedido + Deal Watcher) una sola vez."

    def handle(self, *args, **options):
        self.stdout.write("== Tareas programadas: inicio ==")

        # 1. Precios Bajo Pedido (eBay) ------------------------------------
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
