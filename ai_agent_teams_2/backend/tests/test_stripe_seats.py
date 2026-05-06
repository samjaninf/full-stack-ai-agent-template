"""Tests for Stripe seat limit enforcement."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _org(seats_limit=None, stripe_customer_id=None):
    org = MagicMock()
    org.id = "org-1"
    org.name = "Test Org"
    org.seats_limit = seats_limit
    org.stripe_customer_id = stripe_customer_id
    return org


def _invite(org_id="org-1", role="member"):
    inv = MagicMock()
    inv.organization_id = org_id
    inv.role = role
    inv.status = "pending"
    inv.expires_at = None
    inv.email = "user@example.com"
    return inv


class TestSeatLimitEnforcement:
    """Invitation.accept() enforces seats_limit (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.anyio
    async def test_accept_allowed_when_under_limit(self, mock_db):
        from app.services.invitation import InvitationService

        org = _org(seats_limit=5)
        inv = _invite()

        with (
            patch("app.repositories.invitation_repo.get_by_token", new=AsyncMock(return_value=inv)),
            patch("app.repositories.member_repo.get", new=AsyncMock(return_value=None)),
            patch("app.repositories.organization_repo.get_by_id", new=AsyncMock(return_value=org)),
            patch("app.repositories.member_repo.count_for_org", new=AsyncMock(return_value=3)),
            patch("app.repositories.member_repo.create", new=AsyncMock(return_value=MagicMock())),
            patch("app.repositories.invitation_repo.accept", new=AsyncMock()),
        ):
            svc = InvitationService(mock_db)
            result = await svc.accept("tok", "user-1")
            assert result is inv

    @pytest.mark.anyio
    async def test_accept_blocked_when_at_limit(self, mock_db):
        from app.core.exceptions import PaymentRequiredError
        from app.services.invitation import InvitationService

        org = _org(seats_limit=3)
        inv = _invite()

        with (
            patch("app.repositories.invitation_repo.get_by_token", new=AsyncMock(return_value=inv)),
            patch("app.repositories.member_repo.get", new=AsyncMock(return_value=None)),
            patch("app.repositories.organization_repo.get_by_id", new=AsyncMock(return_value=org)),
            patch("app.repositories.member_repo.count_for_org", new=AsyncMock(return_value=3)),
        ):
            svc = InvitationService(mock_db)
            with pytest.raises(PaymentRequiredError):
                await svc.accept("tok", "user-1")

    @pytest.mark.anyio
    async def test_accept_unlimited_when_no_seats_limit(self, mock_db):
        from app.services.invitation import InvitationService

        org = _org(seats_limit=None)
        inv = _invite()

        with (
            patch("app.repositories.invitation_repo.get_by_token", new=AsyncMock(return_value=inv)),
            patch("app.repositories.member_repo.get", new=AsyncMock(return_value=None)),
            patch("app.repositories.organization_repo.get_by_id", new=AsyncMock(return_value=org)),
            patch("app.repositories.member_repo.count_for_org", new=AsyncMock(return_value=100)),
            patch("app.repositories.member_repo.create", new=AsyncMock(return_value=MagicMock())),
            patch("app.repositories.invitation_repo.accept", new=AsyncMock()),
        ):
            svc = InvitationService(mock_db)
            result = await svc.accept("tok", "user-1")
            assert result is inv


class TestBillingService:
    """BillingService unit tests (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.anyio
    async def test_get_or_create_customer_returns_existing(self, mock_db):
        from app.services.billing import BillingService

        org = _org(stripe_customer_id="cus_existing")
        svc = BillingService(mock_db)
        customer_id = await svc.get_or_create_customer(org)
        assert customer_id == "cus_existing"

    @pytest.mark.anyio
    async def test_create_checkout_raises_when_no_price(self, mock_db):
        from app.core.exceptions import BadRequestError
        from app.services.billing import BillingService

        org = _org(stripe_customer_id="cus_123")

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.STRIPE_DEFAULT_PRICE_ID = ""
            svc = BillingService(mock_db)
            with pytest.raises(BadRequestError):
                await svc.create_checkout_session(
                    org,
                    seats=1,
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )

    @pytest.mark.anyio
    async def test_create_portal_raises_when_no_customer(self, mock_db):
        from app.core.exceptions import BadRequestError
        from app.services.billing import BillingService

        org = _org(stripe_customer_id=None)
        svc = BillingService(mock_db)
        with pytest.raises(BadRequestError):
            await svc.create_portal_session(org)

    @pytest.mark.anyio
    async def test_webhook_invalid_signature_raises(self, mock_db):
        import stripe as _stripe

        from app.core.exceptions import BadRequestError
        from app.services.billing import BillingService

        svc = BillingService(mock_db)
        with (
            patch.object(
                _stripe.Webhook,
                "construct_event",
                side_effect=_stripe.SignatureVerificationError("bad sig", b""),
            ),
            pytest.raises(BadRequestError),
        ):
            await svc.handle_webhook_event(b"payload", "sig")
