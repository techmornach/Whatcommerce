from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BillingPlan, Tenant, User
from app.models.enums import TenantStatus


@dataclass(frozen=True)
class StoreContext:
    phone_e164: str
    user_id: int
    tenant_id: int
    user_display_name: str
    business_name: str
    plan_name: str
    plan_key: str
    max_products: int


def resolve_store_context(db: Session, phone_e164: str) -> StoreContext | None:
    user = (
        db.execute(select(User).where(User.phone_e164 == phone_e164)).scalars().first()
    )
    if user is None or not user.tenant_id:
        return None
    tenant = db.get(Tenant, user.tenant_id)
    if tenant is None or tenant.status != TenantStatus.active:
        return None
    plan = db.get(BillingPlan, tenant.plan_id)
    if plan is None:
        return None
    return StoreContext(
        phone_e164=phone_e164,
        user_id=user.id,
        tenant_id=tenant.id,
        user_display_name=(user.full_name or "").strip() or "there",
        business_name=tenant.business_name,
        plan_name=plan.name,
        plan_key=plan.key,
        max_products=plan.max_products,
    )
