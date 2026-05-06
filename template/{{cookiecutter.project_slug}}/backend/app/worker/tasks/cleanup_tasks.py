{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system and (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) %}
"""Cleanup tasks — periodic purge of old usage events."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

{%- if cookiecutter.use_celery %}
from celery import shared_task
{%- elif cookiecutter.use_taskiq %}
from app.worker.taskiq_app import broker
{%- endif %}

logger = logging.getLogger(__name__)

USAGE_RETENTION_DAYS = 90


async def _run_cleanup_usage_events(days: int = USAGE_RETENTION_DAYS) -> int:
    """Delete usage events older than `days` days. Returns deleted row count."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
{%- if cookiecutter.use_postgresql %}
    from app.db.session import get_worker_db_context
    import app.repositories.usage_event as usage_repo
    from sqlalchemy import text

    async with get_worker_db_context() as db:
        deleted = await usage_repo.delete_older_than(db, cutoff)
        await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_usage_daily"))
    return deleted
{%- elif cookiecutter.use_sqlite %}
    from app.db.session import SessionLocal
    import app.repositories.usage_event as usage_repo

    db = SessionLocal()
    try:
        deleted = usage_repo.delete_older_than(db, cutoff)
        db.commit()
    finally:
        db.close()
    return deleted
{%- elif cookiecutter.use_mongodb %}
    from app.db.session import get_db_session
    import app.repositories.usage_event as usage_repo

    db = await get_db_session()
    return await usage_repo.delete_older_than(db, cutoff)
{%- endif %}


# ─────────────────────────────────────────────────────────────────────────────
# Task declarations
# ─────────────────────────────────────────────────────────────────────────────

{%- if cookiecutter.use_celery %}

@shared_task(bind=True, max_retries=1, ignore_result=True)
def cleanup_usage_events_task(self: Any) -> None:
    """Cron: purge usage events older than 90 days and refresh the daily matview."""
    try:
        count = asyncio.run(_run_cleanup_usage_events())
        logger.info("cleanup_usage_events_done", extra={"deleted": count})
    except Exception as exc:
        logger.exception("cleanup_usage_events_task_failed")
        raise self.retry(exc=exc, countdown=600) from exc

{%- elif cookiecutter.use_taskiq %}

@broker.task
async def cleanup_usage_events_task() -> dict[str, int]:
    """Cron: purge usage events older than 90 days and refresh the daily matview."""
    count = await _run_cleanup_usage_events()
    logger.info("cleanup_usage_events_done", count=count)
    return {"deleted": count}

{%- elif cookiecutter.use_arq %}

async def cleanup_usage_events_task(ctx: dict[str, Any]) -> dict[str, int]:
    """Cron: purge usage events older than 90 days and refresh the daily matview."""
    count = await _run_cleanup_usage_events()
    logger.info(f"cleanup_usage_events_done deleted={count}")
    return {"deleted": count}

{%- endif %}

{%- else %}
"""cleanup_tasks — not enabled."""
{%- endif %}
