"""
Celery tasks for Deal Watcher.

`check_deals` runs every 30 minutes via `CELERY_BEAT_SCHEDULE` (see
`config/settings.py`). It calls the same orchestrator the management command
uses, so behaviour stays consistent.
"""
from __future__ import annotations

import logging

from celery import shared_task

from deal_watcher.services import deal_checker, notifier as notifier_module

logger = logging.getLogger(__name__)


@shared_task(name='deal_watcher.tasks.check_deals', bind=True, max_retries=3)
def check_deals(self):
    """Run a Deal Watcher pass and return a summary dict."""
    try:
        summary = deal_checker.check_all_active(
            notifier=lambda product, snapshot, outcome: notifier_module.notify(product, snapshot, outcome),
            dry_run=False,
        )
        result = {
            'total': summary.total,
            'notified': summary.notified,
            'skipped': summary.skipped,
            'errors': summary.errors,
        }
        logger.info("Deal Watcher Celery run: %s", result)
        return result
    except Exception as exc:
        logger.exception("Fatal error in deal_watcher.check_deals: %s", exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        return {'status': 'failed', 'error': str(exc)}
