"""Internal routes for the Whatcommerce platform WhatsApp worker (global outbound)."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_internal_secret
from app.constants import DEFAULT_PLATFORM_SETTINGS_ID
from app.db.session import get_db
from app.models.platform import PlatformSettings
from app.utils.phone import normalize_phone_e164
from app.services.outbound_queue import (
    WorkerChannel,
    ack_outbound_sent,
    claim_outbound,
    forgive_outbound_after_send,
    outbound_metrics,
    report_outbound_failure,
)

router = APIRouter(
    prefix="/v1/internal/whatcommerce",
    tags=["internal-whatcommerce"],
    dependencies=[Depends(require_internal_secret)],
)

_WH: WorkerChannel = "whatcommerce"

_QR_MAX_LEN = 8192


class WhatcommerceQrBody(BaseModel):
    """Raw pairing string from whatsapp-web.js `qr` event (admin UI renders it)."""
    qr: str = Field(..., min_length=1, max_length=_QR_MAX_LEN)


class WhatcommerceSessionReadyBody(BaseModel):
    """Logged-in WhatsApp user id from whatsapp-web.js (`client.info.wid.user`) — platform bot, not a store."""
    whatsapp_user_e164: str = Field(..., min_length=5, max_length=40)


@router.post("/session-ready")
async def whatcommerce_session_ready(
    body: WhatcommerceSessionReadyBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    digits = normalize_phone_e164(body.whatsapp_user_e164)
    if len(digits) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid whatsapp_user_e164")
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        return {"ok": False, "detail": "platform_settings missing"}
    row.whatcommerce_session_phone_e164 = digits
    row.whatcommerce_session_ready_at = datetime.now(timezone.utc)
    row.whatcommerce_qr_data = None
    await db.commit()
    return {"ok": True, "whatcommerce_session_phone_e164": digits}


@router.post("/qr")
async def whatcommerce_qr_update(
    body: WhatcommerceQrBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        return {"ok": False, "detail": "platform_settings missing"}
    row.whatcommerce_qr_data = body.qr[:_QR_MAX_LEN]
    await db.commit()
    return {"ok": True}


@router.get("/session-control")
async def whatcommerce_session_control(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Polled by the whatcommerce worker to see if the admin requested a new WhatsApp session."""
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        return {"whatcommerce_pending_session_reset": False}
    return {"whatcommerce_pending_session_reset": bool(row.whatcommerce_pending_session_reset)}


@router.post("/session-reset-ack")
async def whatcommerce_session_reset_ack(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Worker calls after destroying the client and deleting `.wwebjs_auth` (before re-initialize)."""
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        return {"ok": False, "detail": "platform_settings missing"}
    row.whatcommerce_pending_session_reset = False
    await db.commit()
    return {"ok": True}


class WhatcommerceClaimBody(BaseModel):
    limit: int = Field(default=15, ge=1, le=50)


class WhatcommerceAckBody(BaseModel):
    ids: list[UUID] = Field(..., min_length=1, max_length=50)


class WhatcommerceReportFailBody(BaseModel):
    ids: list[UUID] = Field(..., min_length=1, max_length=50)
    error: str = Field(..., min_length=1, max_length=2000)
    failure_class: str = Field(default="send", max_length=32)


class WhatcommerceForgiveBody(BaseModel):
    ids: list[UUID] = Field(..., min_length=1, max_length=50)


@router.post("/outbound/claim")
async def claim_whatcommerce_outbound(
    body: WhatcommerceClaimBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    items = await claim_outbound(db, worker_channel=_WH, tenant_id=None, limit=body.limit)
    await db.commit()
    return {"items": items}


@router.post("/outbound/ack")
async def ack_whatcommerce_outbound(
    body: WhatcommerceAckBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    deleted = await ack_outbound_sent(db, worker_channel=_WH, tenant_id=None, ids=body.ids)
    await db.commit()
    return {"ok": True, "deleted": deleted}


@router.post("/outbound/report-fail")
async def report_whatcommerce_outbound_fail(
    body: WhatcommerceReportFailBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    summary = await report_outbound_failure(
        db,
        worker_channel=_WH,
        tenant_id=None,
        ids=body.ids,
        error=body.error,
        failure_class=body.failure_class,
    )
    await db.commit()
    return {"ok": True, **summary}


@router.post("/outbound/forgive")
async def forgive_whatcommerce_outbound(
    body: WhatcommerceForgiveBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    deleted = await forgive_outbound_after_send(db, worker_channel=_WH, tenant_id=None, ids=body.ids)
    await db.commit()
    return {"ok": True, "deleted": deleted}


@router.get("/outbound/metrics")
async def whatcommerce_outbound_metrics(
    db: AsyncSession = Depends(get_db),
    since_hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    return await outbound_metrics(db, since_hours=since_hours)
