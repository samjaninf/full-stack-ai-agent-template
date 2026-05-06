"""UsageService — record AI usage events and debit credits."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.usage_event as usage_repo
from app.billing.credit_service import CreditService
from app.billing.pricing import usage_to_credits
from app.core.config import settings


class UsageService:
    """Record a usage event and debit the corresponding credits."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._credit_svc = CreditService(db)

    async def record(
        self,
        *,
        organization_id: uuid.UUID,
        model: str,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        ai_framework: str = "",
        actor_user_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> int:
        """Persist usage event, compute credits, debit org, return credits charged."""
        credits = usage_to_credits(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            credits_per_usd=settings.CREDITS_PER_USD,
        )

        event = await usage_repo.create(
            self.db,
            organization_id=organization_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            credits_charged=credits,
            ai_framework=ai_framework,
            actor_user_id=actor_user_id,
            conversation_id=conversation_id,
        )

        if credits > 0:
            try:
                await self._credit_svc.debit(
                    organization_id=organization_id,
                    amount=credits,
                    description=f"{model} — {input_tokens + output_tokens} tokens",
                    usage_event_id=event.id,
                )
            except Exception:
                logger.exception(
                    "usage_credit_debit_failed", extra={"org_id": str(organization_id)}
                )

        return credits
