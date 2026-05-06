"""Lifecycle email tasks — trial reminders and low-credits alerts."""

import asyncio
import logging
from datetime import UTC
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Inner helpers (DB + email logic, always async)
# ─────────────────────────────────────────────────────────────────────────────
async def _run_trial_reminders() -> int:
    from datetime import datetime

    import stripe

    import app.repositories.subscription as sub_repo
    from app.core.config import settings
    from app.db.session import get_worker_db_context
    from app.email.service import get_email_service

    sent = 0
    async with get_worker_db_context() as db:
        subs = await sub_repo.get_trialing_ending_soon(db, within_days=3)
        email_svc = get_email_service()
        for sub in subs:
            try:
                customer = stripe.Customer.retrieve(sub.stripe_customer_id)
                now = datetime.now(UTC)
                days_left = (
                    max(1, int((sub.trial_end.timestamp() - now.timestamp()) / 86400))
                    if sub.trial_end
                    else 3
                )
                await email_svc.send_trial_ending(
                    to=customer.email or "",
                    name=customer.name or customer.email or "there",
                    days_left=days_left,
                    upgrade_url=settings.BILLING_SUCCESS_URL,
                )
                sent += 1
            except Exception:
                logger.exception("trial_reminder_email_failed", extra={"sub_id": str(sub.id)})
    return sent


async def _run_low_credits_alerts() -> int:
    import app.repositories.organization as org_repo
    from app.core.config import settings
    from app.db.session import get_worker_db_context
    from app.email.service import get_email_service

    sent = 0
    async with get_worker_db_context() as db:
        rows = await org_repo.get_with_low_credits(db, threshold=settings.CREDITS_LOW_THRESHOLD)
        email_svc = get_email_service()
        for org, owner_email, owner_name in rows:
            try:
                await email_svc.send_low_credits(
                    to=owner_email,
                    name=owner_name,
                    balance=org.credits_balance,
                    topup_url=settings.BILLING_SUCCESS_URL,
                )
                sent += 1
            except Exception:
                logger.exception("low_credits_alert_failed", extra={"org_id": str(org.id)})
    return sent


# ─────────────────────────────────────────────────────────────────────────────
# Task declarations
# ─────────────────────────────────────────────────────────────────────────────
@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_trial_reminders_task(self: Any) -> None:
    """Cron: send trial-ending reminder emails for trials expiring within 3 days."""
    try:
        count = asyncio.run(_run_trial_reminders())
        logger.info("trial_reminders_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_trial_reminders_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc


@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_low_credits_alerts_task(self: Any) -> None:
    """Cron: send low-credits alert emails to orgs below threshold."""
    try:
        count = asyncio.run(_run_low_credits_alerts())
        logger.info("low_credits_alerts_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_low_credits_alerts_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc
