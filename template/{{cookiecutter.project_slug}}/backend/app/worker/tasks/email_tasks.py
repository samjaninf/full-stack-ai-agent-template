{%- if cookiecutter.enable_email and (cookiecutter.enable_billing or cookiecutter.enable_credits_system) and (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) %}
"""Lifecycle email tasks — trial reminders and low-credits alerts."""

import asyncio
import logging
from typing import Any

{%- if cookiecutter.use_celery %}
from celery import shared_task
{%- elif cookiecutter.use_taskiq %}
from app.worker.taskiq_app import broker
{%- endif %}

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Inner helpers (DB + email logic, always async)
# ─────────────────────────────────────────────────────────────────────────────

{%- if cookiecutter.enable_billing %}

{%- if cookiecutter.use_postgresql %}
async def _run_trial_reminders() -> int:
    from datetime import datetime, timezone
    from app.db.session import get_worker_db_context
    import app.repositories.subscription as sub_repo
    import stripe
    from app.email.service import get_email_service
    from app.core.config import settings

    sent = 0
    async with get_worker_db_context() as db:
        subs = await sub_repo.get_trialing_ending_soon(db, within_days=3)
        email_svc = get_email_service()
        for sub in subs:
            try:
                customer = stripe.Customer.retrieve(sub.stripe_customer_id)
                now = datetime.now(timezone.utc)
                days_left = max(1, int((sub.trial_end.timestamp() - now.timestamp()) / 86400)) if sub.trial_end else 3
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

{%- elif cookiecutter.use_sqlite %}
async def _run_trial_reminders() -> int:
    from datetime import datetime, timezone
    from app.db.session import SessionLocal
    import app.repositories.subscription as sub_repo
    import stripe
    from app.email.service import get_email_service
    from app.core.config import settings

    db = SessionLocal()
    sent = 0
    try:
        subs = sub_repo.get_trialing_ending_soon(db, within_days=3)
        email_svc = get_email_service()
        for sub in subs:
            try:
                customer = stripe.Customer.retrieve(sub.stripe_customer_id)
                now = datetime.now(timezone.utc)
                days_left = max(1, int((sub.trial_end.timestamp() - now.timestamp()) / 86400)) if sub.trial_end else 3
                await email_svc.send_trial_ending(
                    to=customer.email or "",
                    name=customer.name or customer.email or "there",
                    days_left=days_left,
                    upgrade_url=settings.BILLING_SUCCESS_URL,
                )
                sent += 1
            except Exception:
                logger.exception("trial_reminder_email_failed", extra={"sub_id": str(sub.id)})
    finally:
        db.close()
    return sent

{%- elif cookiecutter.use_mongodb %}
async def _run_trial_reminders() -> int:
    from datetime import datetime, timezone
    from app.db.session import get_db_session
    import app.repositories.subscription as sub_repo
    import stripe
    from app.email.service import get_email_service
    from app.core.config import settings

    db = await get_db_session()
    sent = 0
    subs = await sub_repo.get_trialing_ending_soon(db, within_days=3)
    email_svc = get_email_service()
    for sub in subs:
        try:
            customer = stripe.Customer.retrieve(sub.stripe_customer_id)
            now = datetime.now(timezone.utc)
            days_left = max(1, int((sub.trial_end.timestamp() - now.timestamp()) / 86400)) if sub.trial_end else 3
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
{%- endif %}

{%- endif %}{# enable_billing #}


{%- if cookiecutter.enable_credits_system %}

{%- if cookiecutter.use_postgresql %}
async def _run_low_credits_alerts() -> int:
    from app.db.session import get_worker_db_context
    import app.repositories.organization as org_repo
    from app.email.service import get_email_service
    from app.core.config import settings

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

{%- elif cookiecutter.use_sqlite %}
async def _run_low_credits_alerts() -> int:
    from app.db.session import SessionLocal
    import app.repositories.organization as org_repo
    from app.email.service import get_email_service
    from app.core.config import settings

    db = SessionLocal()
    sent = 0
    try:
        rows = org_repo.get_with_low_credits(db, threshold=settings.CREDITS_LOW_THRESHOLD)
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
    finally:
        db.close()
    return sent

{%- elif cookiecutter.use_mongodb %}
async def _run_low_credits_alerts() -> int:
    from app.db.session import get_db_session
    import app.repositories.organization as org_repo
    from app.email.service import get_email_service
    from app.core.config import settings

    db = await get_db_session()
    rows = await org_repo.get_with_low_credits(db, threshold=settings.CREDITS_LOW_THRESHOLD)
    sent = 0
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
{%- endif %}

{%- endif %}{# enable_credits_system #}


# ─────────────────────────────────────────────────────────────────────────────
# Task declarations
# ─────────────────────────────────────────────────────────────────────────────

{%- if cookiecutter.use_celery %}

{%- if cookiecutter.enable_billing %}
@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_trial_reminders_task(self: Any) -> None:
    """Cron: send trial-ending reminder emails for trials expiring within 3 days."""
    try:
        count = asyncio.run(_run_trial_reminders())
        logger.info("trial_reminders_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_trial_reminders_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc
{%- endif %}

{%- if cookiecutter.enable_credits_system %}
@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_low_credits_alerts_task(self: Any) -> None:
    """Cron: send low-credits alert emails to orgs below threshold."""
    try:
        count = asyncio.run(_run_low_credits_alerts())
        logger.info("low_credits_alerts_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_low_credits_alerts_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc
{%- endif %}


{%- elif cookiecutter.use_taskiq %}

{%- if cookiecutter.enable_billing %}
@broker.task
async def send_trial_reminders_task() -> dict[str, int]:
    """Cron: send trial-ending reminder emails for trials expiring within 3 days."""
    count = await _run_trial_reminders()
    logger.info("trial_reminders_sent", count=count)
    return {"sent": count}
{%- endif %}

{%- if cookiecutter.enable_credits_system %}
@broker.task
async def send_low_credits_alerts_task() -> dict[str, int]:
    """Cron: send low-credits alert emails to orgs below threshold."""
    count = await _run_low_credits_alerts()
    logger.info("low_credits_alerts_sent", count=count)
    return {"sent": count}
{%- endif %}


{%- elif cookiecutter.use_arq %}

{%- if cookiecutter.enable_billing %}
async def send_trial_reminders_task(ctx: dict[str, Any]) -> dict[str, int]:
    """Cron: send trial-ending reminder emails for trials expiring within 3 days."""
    count = await _run_trial_reminders()
    logger.info(f"trial_reminders_sent count={count}")
    return {"sent": count}
{%- endif %}

{%- if cookiecutter.enable_credits_system %}
async def send_low_credits_alerts_task(ctx: dict[str, Any]) -> dict[str, int]:
    """Cron: send low-credits alert emails to orgs below threshold."""
    count = await _run_low_credits_alerts()
    logger.info(f"low_credits_alerts_sent count={count}")
    return {"sent": count}
{%- endif %}

{%- endif %}

{%- else %}
"""email_tasks — not enabled."""
{%- endif %}
