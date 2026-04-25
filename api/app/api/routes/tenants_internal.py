from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_internal_secret
from app.db.session import get_db
from app.models.tenant import PlanTier, Tenant, TenantStatus

router = APIRouter(
    prefix="/v1/internal/tenants",
    tags=["internal-tenants"],
    dependencies=[Depends(require_internal_secret)],
)


def normalize_phone_e164(raw: str) -> str:
    return "".join(c for c in raw if c.isdigit())


class TenantCreate(BaseModel):
    owner_name: str = Field(min_length=1, max_length=255)
    business_name: str = Field(min_length=1, max_length=255)
    business_address: str = Field(min_length=1, max_length=4000)
    plan_tier: str = Field(default=PlanTier.lite.value)
    billing_period: Literal["monthly", "yearly"] = "monthly"
    onboarding_phone_e164: str = Field(min_length=10, max_length=32)
    owner_email: Optional[EmailStr] = None


class TenantPatch(BaseModel):
    owner_email: Optional[EmailStr] = None


@router.get("")
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    total = await db.scalar(select(func.count()).select_from(Tenant))
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(limit)
    )
    rows = result.scalars().all()
    return {
        "total": int(total or 0),
        "items": [
            {
                "id": str(t.id),
                "owner_name": t.owner_name,
                "business_name": t.business_name,
                "plan_tier": t.plan_tier,
                "billing_period": t.billing_period,
                "status": t.status,
                "plan_expires_at": t.plan_expires_at.isoformat() if t.plan_expires_at else None,
                "onboarding_phone_e164": t.onboarding_phone_e164,
                "owner_email": t.owner_email,
                "last_paystack_reference": t.last_paystack_reference,
                "store_manager_phone_e164": t.store_manager_phone_e164,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(body: TenantCreate, db: AsyncSession = Depends(get_db)) -> dict:
    phone = normalize_phone_e164(body.onboarding_phone_e164)
    if len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid onboarding_phone_e164")

    dup = await db.execute(select(Tenant.id).where(Tenant.onboarding_phone_e164 == phone).limit(1))
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A tenant already exists for this onboarding phone")

    if body.plan_tier not in (e.value for e in PlanTier):
        raise HTTPException(status_code=400, detail="Invalid plan_tier")

    tenant = Tenant(
        owner_name=body.owner_name.strip(),
        business_name=body.business_name.strip(),
        business_address=body.business_address.strip(),
        plan_tier=body.plan_tier,
        billing_period=body.billing_period,
        status=TenantStatus.inactive.value,
        onboarding_phone_e164=phone,
        owner_email=body.owner_email,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return {"id": str(tenant.id), "status": tenant.status}


@router.patch("/{tenant_id}")
async def patch_tenant(
    tenant_id: UUID,
    body: TenantPatch,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if body.owner_email is not None:
        tenant.owner_email = body.owner_email
    await db.commit()
    await db.refresh(tenant)
    return {"id": str(tenant.id), "owner_email": tenant.owner_email}
