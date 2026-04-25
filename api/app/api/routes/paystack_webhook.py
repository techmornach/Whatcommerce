import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import subscription_amount_kobo, subscription_timedelta_days
from app.db.session import get_db
from app.models.paystack_event import PaystackProcessedReference
from app.models.tenant import Tenant, TenantStatus
from app.services.paystack import verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


def _ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/paystack")
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw = await request.body()
    sig = request.headers.get("x-paystack-signature") or ""
    if not verify_webhook_signature(raw, sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("paystack webhook: invalid json")
        return {"ok": False, "reason": "invalid_json"}

    event = payload.get("event")
    if event != "charge.success":
        return {"ok": True, "ignored": event}

    data = payload.get("data") or {}
    ref = data.get("reference")
    if not ref:
        return {"ok": False, "reason": "no_reference"}

    try:
        amount = int(data.get("amount") or 0)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "bad_amount"}

    currency = (data.get("currency") or "").upper()
    if currency != "NGN":
        logger.warning("paystack webhook: unexpected currency %s ref=%s", currency, ref)
        return {"ok": False, "reason": "bad_currency"}

    metadata = data.get("metadata") or {}
    tenant_id_raw = metadata.get("tenant_id")

    result = await db.execute(select(Tenant).where(Tenant.last_paystack_reference == str(ref)))
    tenant = result.scalar_one_or_none()
    if tenant is None and tenant_id_raw:
        try:
            tenant = await db.get(Tenant, UUID(str(tenant_id_raw)))
        except (ValueError, TypeError):
            tenant = None

    if tenant is None:
        logger.warning("paystack webhook: no tenant for reference=%s", ref)
        return {"ok": True, "ignored": "unknown_reference"}

    expected = await subscription_amount_kobo(db, tenant.plan_tier, tenant.billing_period)
    if amount != expected:
        logger.warning(
            "paystack webhook: amount mismatch tenant=%s expected_kobo=%s got=%s ref=%s",
            tenant.id,
            expected,
            amount,
            ref,
        )
        return {"ok": False, "reason": "amount_mismatch"}

    stmt = (
        insert(PaystackProcessedReference)
        .values(reference=str(ref), tenant_id=tenant.id)
        .on_conflict_do_nothing(index_elements=["reference"])
        .returning(PaystackProcessedReference.reference)
    )
    res = await db.execute(stmt)
    if res.scalar_one_or_none() is None:
        return {"ok": True, "duplicate": True}

    now = datetime.now(timezone.utc)
    base = tenant.plan_expires_at or now
    base = _ensure_aware_utc(base)
    if base < now:
        base = now
    days = subscription_timedelta_days(tenant.billing_period)
    tenant.plan_expires_at = base + timedelta(days=days)
    tenant.status = TenantStatus.active.value
    tenant.wa_link_token = uuid.uuid4()
    tenant.wa_link_expires_at = now + timedelta(minutes=10)

    await db.commit()
    return {"ok": True, "tenant_id": str(tenant.id), "plan_expires_at": tenant.plan_expires_at.isoformat()}
