"""Internal routes for store-manager worker (session registration)."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_internal_secret
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.outbound_queue import (
    WorkerChannel,
    ack_outbound_sent,
    claim_outbound,
    forgive_outbound_after_send,
    report_outbound_failure,
)
from app.utils.phone import normalize_phone_e164


def _digits_only_sql(column):
    """PostgreSQL: strip non-digits for comparisons with legacy rows."""
    return func.regexp_replace(column, "[^0-9]", "", "g")

router = APIRouter(
    prefix="/v1/internal/store-manager",
    tags=["internal-store-manager"],
    dependencies=[Depends(require_internal_secret)],
)

_SM: WorkerChannel = "store_manager"


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class RegisterStoreSessionBody(BaseModel):
    tenant_id: UUID
    store_manager_phone_e164: str = Field(..., min_length=8, max_length=32)
    wa_link_token: Optional[UUID] = None


@router.post("/register-session")
async def register_store_manager_session(
    body: RegisterStoreSessionBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Called from the store-manager worker on WhatsApp `ready`.
    Binds this WhatsApp login to `tenants.store_manager_phone_e164` and clears the post-payment link token.
    """
    phone = normalize_phone_e164(body.store_manager_phone_e164)
    if len(phone) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")

    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    now = datetime.now(timezone.utc)
    if (
        tenant.wa_link_token is not None
        and tenant.wa_link_expires_at is not None
        and _utc(tenant.wa_link_expires_at) >= now
    ):
        if body.wa_link_token is None or body.wa_link_token != tenant.wa_link_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Valid wa_link_token required while the post-payment link is active",
            )

    if phone == normalize_phone_e164(tenant.onboarding_phone_e164):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store manager WhatsApp must not be the same number as the onboarding / owner chat",
        )

    dup_sm = await db.execute(
        select(Tenant.id)
        .where(
            Tenant.id != tenant.id,
            Tenant.store_manager_phone_e164.isnot(None),
            _digits_only_sql(Tenant.store_manager_phone_e164) == phone,
        )
        .limit(1)
    )
    if dup_sm.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This WhatsApp number is already linked as store manager for another shop",
        )

    dup_onb = await db.execute(
        select(Tenant.id).where(_digits_only_sql(Tenant.onboarding_phone_e164) == phone).limit(1)
    )
    if dup_onb.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This number is already used as a platform onboarding account",
        )

    if tenant.store_manager_phone_e164:
        if normalize_phone_e164(tenant.store_manager_phone_e164) == phone:
            tenant.wa_link_token = None
            tenant.wa_link_expires_at = None
            await db.commit()
            return {"ok": True, "idempotent": True, "store_manager_phone_e164": phone}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant already has a different store manager number; clear it in the database to replace",
        )

    tenant.store_manager_phone_e164 = phone
    tenant.wa_link_token = None
    tenant.wa_link_expires_at = None
    await db.commit()
    return {"ok": True, "store_manager_phone_e164": phone}


class OutboundClaimBody(BaseModel):
    tenant_id: UUID
    limit: int = Field(default=10, ge=1, le=50)


class OutboundAckBody(BaseModel):
    tenant_id: UUID
    ids: list[UUID] = Field(..., min_length=1, max_length=50)


@router.post("/outbound/claim")
async def claim_store_manager_outbound(
    body: OutboundClaimBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Claim pending outbound rows for `worker_channel=store_manager` for this tenant only.
    """
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    items = await claim_outbound(
        db, worker_channel=_SM, tenant_id=body.tenant_id, limit=body.limit
    )
    await db.commit()
    return {"items": items}


@router.post("/outbound/ack")
async def ack_store_manager_outbound(
    body: OutboundAckBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    deleted = await ack_outbound_sent(
        db, worker_channel=_SM, tenant_id=body.tenant_id, ids=body.ids
    )
    await db.commit()
    return {"ok": True, "deleted": deleted}


class OutboundReportFailBody(BaseModel):
    tenant_id: UUID
    ids: list[UUID] = Field(..., min_length=1, max_length=50)
    error: str = Field(..., min_length=1, max_length=2000)
    failure_class: str = Field(default="send", max_length=32)


class OutboundForgiveBody(BaseModel):
    tenant_id: UUID
    ids: list[UUID] = Field(..., min_length=1, max_length=50)


@router.post("/outbound/report-fail")
async def report_store_manager_outbound_fail(
    body: OutboundReportFailBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    summary = await report_outbound_failure(
        db,
        worker_channel=_SM,
        tenant_id=body.tenant_id,
        ids=body.ids,
        error=body.error,
        failure_class=body.failure_class,
    )
    await db.commit()
    return {"ok": True, **summary}


@router.post("/outbound/forgive")
async def forgive_store_manager_outbound(
    body: OutboundForgiveBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    deleted = await forgive_outbound_after_send(
        db, worker_channel=_SM, tenant_id=body.tenant_id, ids=body.ids
    )
    await db.commit()
    return {"ok": True, "deleted": deleted}
