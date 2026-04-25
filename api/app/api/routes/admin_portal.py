"""JWT-protected dashboard API for platform admins (Whatcommerce ops, not tenant store managers)."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_super_admin
from app.constants import DEFAULT_PLATFORM_SETTINGS_ID
from app.core.security import create_admin_access_token, hash_password
from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser
from app.models.billing_plan import BillingPlan
from app.models.platform import PlatformSettings

router = APIRouter(prefix="/v1/admin", tags=["admin-portal"])


def _admin_json(u: AdminUser) -> dict[str, Any]:
    return {
        "id": str(u.id),
        "email": u.email,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "created_by_id": str(u.created_by_id) if u.created_by_id else None,
    }


@router.get("/me")
async def admin_me(admin: AdminUser = Depends(get_current_admin)) -> dict[str, Any]:
    return _admin_json(admin)


class AdminSelfPatchBody(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


@router.patch("/me")
async def admin_patch_me(
    body: AdminSelfPatchBody,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, Any]:
    """Update own profile. Super admins may change email; any admin may change password."""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    updated = False

    if "email" in data and data["email"] is not None:
        if admin.role != AdminRole.super_admin.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins may change their email",
            )
        new_email = str(data["email"]).strip().lower()
        if new_email != admin.email:
            dup = await db.execute(
                select(AdminUser.id).where(AdminUser.email == new_email, AdminUser.id != admin.id).limit(1)
            )
            if dup.scalar_one_or_none() is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
            admin.email = new_email
            updated = True

    if "password" in data and data["password"] is not None:
        admin.password_hash = hash_password(data["password"])
        updated = True

    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes")

    await db.commit()
    await db.refresh(admin)
    out = _admin_json(admin)
    out["access_token"] = create_admin_access_token(
        admin_id=admin.id,
        email=admin.email,
        role=admin.role,
    )
    return out


class CreateAdminBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: AdminRole = AdminRole.admin


@router.get("/admins")
async def list_admins(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    r = await db.execute(select(AdminUser).order_by(AdminUser.created_at.asc()))
    rows = r.scalars().all()
    return {"admins": [_admin_json(u) for u in rows]}


@router.post("/admins")
async def create_admin(
    body: CreateAdminBody,
    db: AsyncSession = Depends(get_db),
    actor: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    email = body.email.strip().lower()
    exists = await db.execute(select(AdminUser.id).where(AdminUser.email == email).limit(1))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    u = AdminUser(
        email=email,
        password_hash=hash_password(body.password),
        role=body.role.value,
        is_active=True,
        created_by_id=actor.id,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return _admin_json(u)


@router.post("/admins/{target_id}/deactivate")
async def deactivate_admin(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    if target_id == actor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
    u = await db.get(AdminUser, target_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    u.is_active = False
    await db.commit()
    return {"ok": True, "id": str(u.id)}


class AdminPlatformPatch(BaseModel):
    knowledge_base_text: Optional[str] = None


def _platform_admin_json(row: PlatformSettings) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "knowledge_base_text": row.knowledge_base_text,
        "whatcommerce_session_phone_e164": row.whatcommerce_session_phone_e164,
        "whatcommerce_session_ready_at": row.whatcommerce_session_ready_at.isoformat()
        if row.whatcommerce_session_ready_at
        else None,
        "whatcommerce_pending_session_reset": bool(row.whatcommerce_pending_session_reset),
        "whatcommerce_qr_data": row.whatcommerce_qr_data,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/platform")
async def admin_get_platform(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict[str, Any]:
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform settings not initialized")
    return _platform_admin_json(row)


@router.patch("/platform")
async def admin_patch_platform(
    body: AdminPlatformPatch,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict[str, Any]:
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform settings not initialized")
    data = body.model_dump(exclude_unset=True)
    if "knowledge_base_text" in data:
        v = data["knowledge_base_text"]
        row.knowledge_base_text = (v if isinstance(v, str) else str(v)) if v is not None else None
    await db.commit()
    await db.refresh(row)
    return _platform_admin_json(row)


@router.post("/platform/whatcommerce-session-replacement")
async def admin_request_whatcommerce_session_replacement(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict[str, Any]:
    """Clear stored session metadata and ask the whatcommerce worker to wipe LocalAuth and show QR again."""
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform settings not initialized")
    row.whatcommerce_pending_session_reset = True
    row.whatcommerce_session_phone_e164 = None
    row.whatcommerce_session_ready_at = None
    row.whatcommerce_qr_data = None
    await db.commit()
    await db.refresh(row)
    return _platform_admin_json(row)


class BillingPlanOut(BaseModel):
    tier: str
    monthly_amount_ngn: int
    yearly_amount_ngn: Optional[int] = None
    max_products: int
    max_users: int
    is_active: bool


class BillingPlanPatch(BaseModel):
    monthly_amount_ngn: Optional[int] = Field(default=None, ge=0)
    yearly_amount_ngn: Optional[int] = Field(default=None, ge=0)
    max_products: Optional[int] = Field(default=None, ge=0)
    max_users: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


def _plan_json(p: BillingPlan) -> dict[str, Any]:
    return {
        "tier": p.tier,
        "monthly_amount_ngn": int(p.monthly_amount_ngn),
        "yearly_amount_ngn": int(p.yearly_amount_ngn) if p.yearly_amount_ngn is not None else None,
        "max_products": int(p.max_products),
        "max_users": int(p.max_users),
        "is_active": bool(p.is_active),
    }


@router.get("/billing/plans")
async def admin_list_billing_plans(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    r = await db.execute(select(BillingPlan).order_by(BillingPlan.monthly_amount_ngn.asc()))
    rows = r.scalars().all()
    return {"plans": [_plan_json(p) for p in rows]}


@router.patch("/billing/plans/{tier}")
async def admin_patch_billing_plan(
    tier: str,
    body: BillingPlanPatch,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    t = (tier or "").strip().lower()
    if not t:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier")
    plan = await db.get(BillingPlan, t)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(plan, k, v)
    await db.commit()
    await db.refresh(plan)
    return _plan_json(plan)
