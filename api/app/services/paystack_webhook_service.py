"""
Process Paystack webhook events: idempotent activation on charge.success.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BillingPlan,
    OnboardingSession,
    PaystackProcessedReference,
    Tenant,
    User,
)
from app.models.enums import OnboardingState, TenantStatus, UserRole
from app.services.whatsapp_outbound import (
    notify_user_payment_confirmed,
    notify_user_payment_failed,
)

logger = logging.getLogger(__name__)

LAGOS = ZoneInfo("Africa/Lagos")
_REF_TENANT = re.compile(r"^wc-t(\d+)-", re.IGNORECASE)


def process_paystack_payload(db: Session, payload: dict[str, Any]) -> dict[str, str]:
    event = str(payload.get("event") or "")
    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}

    if event == "charge.success":
        return _handle_charge_success(db, data)
    if event == "charge.failed":
        return _handle_charge_failed(db, data)
    logger.info("Paystack webhook ignored event=%s", event)
    return {"result": "ignored", "event": event}


def _handle_charge_success(db: Session, data: dict[str, Any]) -> dict[str, str]:
    reference = str(data.get("reference") or "").strip()
    if not reference:
        logger.warning("charge.success missing reference")
        return {"result": "ignored", "reason": "no_reference"}

    if (
        db.execute(
            select(PaystackProcessedReference).where(
                PaystackProcessedReference.reference == reference
            )
        )
        .scalars()
        .first()
    ):
        logger.info("Duplicate Paystack reference=%s (skip)", reference)
        return {"result": "duplicate", "reference": reference}

    status = str(data.get("status") or "").lower()
    if status and status != "success":
        logger.warning("charge.success status=%s ref=%s", status, reference)
        return {"result": "ignored", "reason": "not_success_status"}

    currency = str(data.get("currency") or "NGN").upper()
    if currency != "NGN":
        logger.warning("Unsupported currency %s ref=%s", currency, reference)
        return {"result": "ignored", "reason": "currency"}

    amount_kobo = _as_int(data.get("amount"))
    if amount_kobo <= 0:
        logger.warning("Invalid amount ref=%s", reference)
        return {"result": "ignored", "reason": "amount"}

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    tenant_id = _meta_int(metadata, "tenant_id")
    if not tenant_id:
        m = _REF_TENANT.match(reference)
        if m:
            tenant_id = int(m.group(1))
    if not tenant_id:
        logger.warning("Could not resolve tenant_id for ref=%s", reference)
        return {"result": "ignored", "reason": "tenant_id"}

    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        logger.warning("Tenant %s not found for ref=%s", tenant_id, reference)
        return {"result": "ignored", "reason": "tenant_missing"}

    if tenant.status == TenantStatus.active:
        _record_processed(db, reference, tenant_id)
        db.commit()
        return {"result": "already_active", "reference": reference}

    plan = db.get(BillingPlan, tenant.plan_id)
    if not plan:
        logger.error("Billing plan missing for tenant=%s", tenant_id)
        return {"result": "error", "reason": "plan_missing"}

    interval = str(metadata.get("billing_interval") or "monthly").lower()
    if interval not in ("monthly", "yearly"):
        interval = "monthly"

    expected_ngn = (
        plan.price_monthly_ngn if interval == "monthly" else plan.price_yearly_ngn
    )
    expected_kobo = max(1, expected_ngn) * 100
    if amount_kobo != expected_kobo:
        logger.warning(
            "Amount mismatch ref=%s expected_kobo=%s got=%s",
            reference,
            expected_kobo,
            amount_kobo,
        )
        return {"result": "ignored", "reason": "amount_mismatch"}

    now = datetime.now(UTC)
    if interval == "yearly":
        ends = now + relativedelta(years=1)
    else:
        ends = now + relativedelta(months=1)

    tenant.status = TenantStatus.active
    tenant.subscription_ends_at = ends
    tenant.paystack_last_reference = reference
    db.add(tenant)

    _record_processed(db, reference, tenant_id)

    mark_onboarding_complete_for_tenant(db, tenant.id)

    owner = (
        db.execute(
            select(User).where(User.tenant_id == tenant.id, User.role == UserRole.owner)
        )
        .scalars()
        .first()
    )
    db.commit()

    if owner:
        fmt = ends.astimezone(LAGOS).strftime("%d %b %Y %H:%M %Z")
        body = (
            f"Payment received! Your Whatcommerce store *{tenant.business_name}* is now "
            f"*active*.\n\n"
            f"Your current plan renews around *{fmt}*.\n\n"
            "Ask me to *list products*, *add a product*, or say *help* for more."
        )
        try:
            notify_user_payment_confirmed(
                db=db, phone_e164=owner.phone_e164, text=body
            )
        except Exception as e:
            logger.exception("WhatsApp notify failed (activation still saved): %s", e)

    logger.info("Activated tenant=%s ref=%s until=%s", tenant_id, reference, ends.isoformat())
    return {"result": "activated", "tenant_id": str(tenant_id), "reference": reference}


def _handle_charge_failed(db: Session, data: dict[str, Any]) -> dict[str, str]:
    """Notify user; do not change tenant. Webhook is source of truth for failure."""
    reference = str(data.get("reference") or "").strip()
    if not reference:
        return {"result": "ignored", "reason": "no_reference"}

    if (
        db.execute(
            select(PaystackProcessedReference).where(
                PaystackProcessedReference.reference == reference
            )
        )
        .scalars()
        .first()
    ):
        return {"result": "duplicate", "reference": reference}

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    tenant_id = _meta_int(metadata, "tenant_id")
    if not tenant_id:
        m = _REF_TENANT.match(reference)
        if m:
            tenant_id = int(m.group(1))
    if not tenant_id:
        return {"result": "ignored", "reason": "tenant_id"}

    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        return {"result": "ignored", "reason": "tenant_missing"}

    gw = data.get("gateway_response")
    if isinstance(gw, dict):
        gateway = str(gw.get("message") or gw.get("responsecode") or gw)[:300]
    else:
        gateway = str(gw or data.get("message") or "failed")[:300]
    _record_failed_processed(db, reference, tenant_id)
    _merge_onboarding_payment_event(db, tenant_id, "charge_failed", reference, gateway)
    db.commit()

    owner = (
        db.execute(
            select(User).where(User.tenant_id == tenant.id, User.role == UserRole.owner)
        )
        .scalars()
        .first()
    )
    if owner:
        body = (
            f"Paystack reported that payment *{reference}* did *not* complete "
            f"({gateway}).\n\n"
            f"Open the payment link again and try once more, or type *I have paid* after paying. "
            f"Your store will activate only when Paystack sends us a *successful* charge."
        )
        try:
            notify_user_payment_failed(
                db=db, phone_e164=owner.phone_e164, text=body
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("WhatsApp notify failed: %s", e)

    logger.info("charge.failed recorded tenant=%s ref=%s", tenant_id, reference)
    return {"result": "payment_failed", "tenant_id": str(tenant_id), "reference": reference}


def _record_failed_processed(db: Session, reference: str, tenant_id: int) -> None:
    db.add(
        PaystackProcessedReference(
            reference=reference,
            tenant_id=tenant_id,
            event_type="charge.failed",
        )
    )
    db.flush()


def _merge_onboarding_payment_event(
    db: Session, tenant_id: int, key: str, reference: str, detail: str
) -> None:
    session = (
        db.execute(
            select(OnboardingSession).where(OnboardingSession.tenant_id == tenant_id)
        )
        .scalars()
        .first()
    )
    if session is None:
        return
    merged = {
        **dict(session.data),
        f"last_{key}": datetime.now(UTC).isoformat(),
        "last_paystack_reference": reference,
        "last_paystack_fail_reason": (detail or "")[:500],
    }
    session.data = merged
    db.add(session)


def _record_processed(db: Session, reference: str, tenant_id: int) -> None:
    db.add(
        PaystackProcessedReference(
            reference=reference,
            tenant_id=tenant_id,
            event_type="charge.success",
        )
    )
    db.flush()


def mark_onboarding_complete_for_tenant(db: Session, tenant_id: int) -> None:
    """Set onboarding session to complete when payment succeeds (webhook)."""
    _mark_onboarding_complete_data(db, tenant_id)


def _mark_onboarding_complete_data(db: Session, tenant_id: int) -> None:
    session = (
        db.execute(
            select(OnboardingSession).where(OnboardingSession.tenant_id == tenant_id)
        )
        .scalars()
        .first()
    )
    if session is None:
        return
    merged = {
        **dict(session.data),
        "activated_at": datetime.now(UTC).isoformat(),
    }
    session.data = merged
    session.state = OnboardingState.complete
    db.add(session)


def _meta_int(meta: dict[str, Any], key: str) -> int:
    v = meta.get(key)
    if v is None:
        return 0
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


def _as_int(v: Any) -> int:
    if v is None:
        return 0
    if isinstance(v, int):
        return v
    try:
        return int(str(v).strip())
    except ValueError:
        return 0
