import logging
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BillingPlan, OnboardingSession, Tenant, User
from app.models.enums import TenantStatus, UserRole
from app.services.paystack_client import initialize_transaction

logger = logging.getLogger(__name__)

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", re.IGNORECASE)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def parse_plan_key(text: str) -> str | None:
    t = clean_text(text).lower().replace(" ", "_")
    if t in {"lite", "1"}:
        return "lite"
    if t in {"standard", "2"}:
        return "standard"
    if t in {"premium", "3"}:
        return "premium"
    if "lite" in t:
        return "lite"
    if "standard" in t or "std" in t:
        return "standard"
    if "premium" in t or "pro" in t:
        return "premium"
    return None


def parse_billing_interval(text: str) -> str | None:
    t = clean_text(text).lower()
    if t in {"m", "month", "monthly", "1"}:
        return "monthly"
    if t in {"y", "year", "yearly", "annual", "annually", "2"}:
        return "yearly"
    if "month" in t:
        return "monthly"
    if "year" in t or "annual" in t:
        return "yearly"
    return None


def valid_email(s: str) -> bool:
    e = clean_text(s).lower()
    return bool(_EMAIL.match(e)) and len(e) <= 512


def create_tenant_and_checkout(
    db: Session,
    session: OnboardingSession,
    plan: BillingPlan,
    amount_ngn: int,
) -> tuple[str, str, int, int]:
    data = session.data
    full_name = str(data.get("full_name") or "")
    business_name = str(data.get("business_name") or "")
    business_address = str(data.get("business_address") or "")
    email = str(data.get("email") or "")
    if not (full_name and business_name and business_address and email):
        raise ValueError("Incomplete onboarding data")

    phone = session.phone_e164
    user = (
        db.execute(select(User).where(User.phone_e164 == phone)).scalars().first()
    )
    if user and user.tenant_id:
        t0 = db.get(Tenant, user.tenant_id)
        if t0 and t0.status == TenantStatus.active:
            raise ValueError("Already active")
    if user is None:
        user = User(
            phone_e164=phone,
            full_name=full_name,
            email=email,
            role=UserRole.owner,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = full_name
        user.email = email
        db.add(user)
        db.flush()

    tenant: Tenant | None = None
    if user.tenant_id:
        tenant = db.get(Tenant, user.tenant_id)
        if not tenant:
            user.tenant_id = None
            db.add(user)
            db.flush()
        if tenant is not None:
            tenant.business_name = business_name
            tenant.business_address = business_address
            tenant.contact_email = email
            tenant.plan_id = plan.id
            tenant.status = TenantStatus.inactive
            db.add(tenant)
            db.flush()
    if user.tenant_id is None or tenant is None:
        tenant = Tenant(
            business_name=business_name,
            business_address=business_address,
            contact_email=email,
            plan_id=plan.id,
            status=TenantStatus.inactive,
        )
        db.add(tenant)
        db.flush()
        user.tenant_id = tenant.id
        db.add(user)
        db.flush()

    reference = f"wc-t{tenant.id}-{secrets.token_hex(4)}"
    meta = {
        "tenant_id": tenant.id,
        "user_id": user.id,
        "plan_key": plan.key,
        "billing_interval": str(data.get("billing_interval") or "monthly"),
    }
    url, ref = initialize_transaction(
        email=email,
        amount_ngn=amount_ngn,
        reference=reference,
        metadata=meta,
    )
    return url, ref, tenant.id, user.id
