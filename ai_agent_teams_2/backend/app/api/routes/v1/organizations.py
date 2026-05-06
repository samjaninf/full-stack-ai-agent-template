"""Organization CRUD routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, OrganizationSvc
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationList,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter()


@router.get("", response_model=OrganizationList)
async def list_organizations(
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """List all organizations the current user belongs to."""
    rows = await service.list_for_user(user.id)
    items = [
        OrganizationRead(
            id=row["org"].id,
            name=row["org"].name,
            slug=row["org"].slug,
            is_personal=row["org"].is_personal,
            avatar_url=row["org"].avatar_url,
            member_count=row["member_count"],
            role=row["role"],
            created_at=row["org"].created_at,
            updated_at=row["org"].updated_at,
            subscription_tier=getattr(row["org"], "subscription_tier", "free"),
            credits_balance=getattr(row["org"], "credits_balance", 0),
        )
        for row in rows
    ]
    return OrganizationList(items=items, total=len(items))


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Create a new organization. The requesting user becomes Owner."""
    org = await service.create(data, owner_id=user.id)
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 1)
    role = next((r["role"] for r in rows if r["org"].id == org.id), "owner")
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        avatar_url=org.avatar_url,
        member_count=member_count,
        role=role,
        created_at=org.created_at,
        updated_at=org.updated_at,
        subscription_tier=getattr(org, "subscription_tier", "free"),
        credits_balance=getattr(org, "credits_balance", 0),
    )


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Get a single organization the current user is a member of."""
    org, membership = await service.get_for_user(org_id, user.id)
    # member_count is fetched inline via get_for_user flow — use service
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 0)
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        avatar_url=org.avatar_url,
        member_count=member_count,
        role=membership.role,
        created_at=org.created_at,
        updated_at=org.updated_at,
        subscription_tier=getattr(org, "subscription_tier", "free"),
        credits_balance=getattr(org, "credits_balance", 0),
    )


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Update organization name or avatar. Requires Admin or Owner role."""
    org = await service.update(org_id, data, requester_id=user.id)
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 0)
    role = next((r["role"] for r in rows if r["org"].id == org.id), "member")
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        avatar_url=org.avatar_url,
        member_count=member_count,
        role=role,
        created_at=org.created_at,
        updated_at=org.updated_at,
        subscription_tier=getattr(org, "subscription_tier", "free"),
        credits_balance=getattr(org, "credits_balance", 0),
    )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_organization(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
) -> None:
    """Delete an organization. Requires Owner role. Personal orgs cannot be deleted."""
    await service.delete(org_id, requester_id=user.id)
