"""Handlers for invoice.* webhook events."""

import logging

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.credit_transaction as credit_tx_repo
import app.repositories.subscription as sub_repo
from app.db.models.credit_transaction import CreditTransactionType

logger = logging.getLogger(__name__)


def _format_amount(invoice) -> str:
    amount = (invoice.amount_paid or invoice.amount_due or 0) / 100
    currency = (invoice.currency or "usd").upper()
    return f"{currency} {amount:.2f}"


async def _send_payment_succeeded_email(invoice) -> None:
    try:
        from app.core.config import settings
        from app.services.email.service import get_email_service

        email_svc = get_email_service()
        await email_svc.send_payment_succeeded(
            to=invoice.customer_email or "",
            name=invoice.customer_name or invoice.customer_email or "there",
            plan_name=invoice.lines.data[0].description
            if invoice.lines and invoice.lines.data
            else "subscription",
            amount=_format_amount(invoice),
            invoice_url=invoice.hosted_invoice_url or settings.BILLING_PORTAL_RETURN_URL,
        )
    except Exception:
        logger.exception("email_payment_succeeded_failed")


async def _send_payment_failed_email(invoice) -> None:
    try:
        from app.core.config import settings
        from app.services.email.service import get_email_service

        email_svc = get_email_service()
        await email_svc.send_payment_failed(
            to=invoice.customer_email or "",
            name=invoice.customer_name or invoice.customer_email or "there",
            amount=_format_amount(invoice),
            update_url=settings.BILLING_PORTAL_RETURN_URL,
        )
    except Exception:
        logger.exception("email_payment_failed_failed")


async def handle_payment_succeeded(db: AsyncSession, event: stripe.Event) -> None:
    invoice = event.data.object
    if invoice.billing_reason not in (
        "subscription_create",
        "subscription_cycle",
        "subscription_update",
    ):
        return

    sub = await sub_repo.get_by_stripe_id(db, invoice.subscription)
    if not sub:
        logger.warning("invoice_sub_not_found", subscription_id=invoice.subscription)
        return
    if invoice.billing_reason in ("subscription_create", "subscription_cycle"):
        plan = sub.price.plan if hasattr(sub, "price") and sub.price else None
        if plan:
            monthly_grant = (
                plan.monthly_credits_base + plan.monthly_credits_per_seat * sub.seats_quantity
            )
            if monthly_grant > 0:
                await credit_tx_repo.create(
                    db,
                    organization_id=sub.organization_id,
                    delta=monthly_grant,
                    balance_after=0,
                    type=CreditTransactionType.GRANT_SUBSCRIPTION,
                    description=f"Monthly credits — {plan.display_name}",
                    stripe_reference=invoice.id,
                )

    await _send_payment_succeeded_email(invoice)


async def handle_payment_failed(db: AsyncSession, event: stripe.Event) -> None:
    invoice = event.data.object
    logger.warning(
        "invoice_payment_failed", invoice_id=invoice.id, subscription_id=invoice.subscription
    )
    await _send_payment_failed_email(invoice)


async def handle_upcoming(db: AsyncSession, event: stripe.Event) -> None:
    invoice = event.data.object
    logger.info("invoice_upcoming", invoice_id=invoice.id, subscription_id=invoice.subscription)
