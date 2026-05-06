"""Cleanup tasks — periodic purge of old usage events."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)

USAGE_RETENTION_DAYS = 90


async def _run_cleanup_usage_events(days: int = USAGE_RETENTION_DAYS) -> int:
    """Delete usage events older than `days` days. Returns deleted row count."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    from sqlalchemy import text

    import app.repositories.usage_event as usage_repo
    from app.db.session import get_worker_db_context

    async with get_worker_db_context() as db:
        deleted = await usage_repo.delete_older_than(db, cutoff)
        await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_usage_daily"))
    return deleted


# ─────────────────────────────────────────────────────────────────────────────
# Task declarations
# ─────────────────────────────────────────────────────────────────────────────


@shared_task(bind=True, max_retries=1, ignore_result=True)
def cleanup_usage_events_task(self: Any) -> None:
    """Cron: purge usage events older than 90 days and refresh the daily matview."""
    try:
        count = asyncio.run(_run_cleanup_usage_events())
        logger.info("cleanup_usage_events_done", extra={"deleted": count})
    except Exception as exc:
        logger.exception("cleanup_usage_events_task_failed")
        raise self.retry(exc=exc, countdown=600) from exc
