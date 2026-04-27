from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import (
    AdminUser,
    BillingPlan,
    ConversationEvent,
    Order,
    Product,
    Tenant,
    User,
    UserRole,
)

router = APIRouter(prefix="/api/admin/tenants", tags=["admin"])


class TenantListItem(BaseModel):
    id: int
    business_name: str
    contact_email: str
    plan_key: str
    plan_name: str
    status: str
    subscription_ends_at: str | None
    owner_phone_e164: str | None
    owner_name: str | None
    product_count: int
    order_count: int
    last_message_at: str | None


@router.get("", response_model=list[TenantListItem])
def list_tenants(
    q: str | None = Query(
        default=None,
        max_length=200,
        description="Search: business, email, phone, owner, or tenant id",
    ),
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[TenantListItem]:
    stmt = select(Tenant)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        id_match = [int(needle)] if needle.isdigit() else []
        ors = [
            Tenant.business_name.ilike(like),
            Tenant.contact_email.ilike(like),
        ]
        if id_match:
            ors.append(Tenant.id == id_match[0])
        user_tenants = (
            select(User.tenant_id)
            .where(
                User.tenant_id.isnot(None),
                or_(
                    User.phone_e164.ilike(like),
                    User.full_name.ilike(like),
                    User.email.ilike(like),
                ),
            )
            .distinct()
        )
        ors.append(Tenant.id.in_(user_tenants))
        stmt = stmt.where(or_(*ors))
    tenants = list(db.execute(stmt.order_by(Tenant.id.desc())).scalars().all())
    tids = [t.id for t in tenants]
    if not tids:
        return []

    last_by_tid: dict[int, object] = {}
    for row in (
        db.execute(
            select(ConversationEvent.tenant_id, func.max(ConversationEvent.created_at))
            .where(ConversationEvent.tenant_id.in_(tids))
            .group_by(ConversationEvent.tenant_id)
        )
    ).all():
        if row[0] is not None:
            last_by_tid[int(row[0])] = row[1]

    prod_count: dict[int, int] = {}
    for row in (
        db.execute(
            select(Product.tenant_id, func.count())
            .where(Product.tenant_id.in_(tids))
            .group_by(Product.tenant_id)
        )
    ).all():
        if row[0] is not None:
            prod_count[int(row[0])] = int(row[1] or 0)

    ord_count: dict[int, int] = {}
    for row in (
        db.execute(
            select(Order.tenant_id, func.count())
            .where(Order.tenant_id.in_(tids))
            .group_by(Order.tenant_id)
        )
    ).all():
        if row[0] is not None:
            ord_count[int(row[0])] = int(row[1] or 0)

    out: list[TenantListItem] = []
    for t in tenants:
        plan = db.get(BillingPlan, t.plan_id)
        plan_key = plan.key if plan else "unknown"
        plan_name = plan.name if plan else "Unknown"
        owner = (
            db.execute(
                select(User).where(User.tenant_id == t.id, User.role == UserRole.owner)
            )
            .scalars()
            .first()
        )
        last_m = last_by_tid.get(t.id)
        out.append(
            TenantListItem(
                id=t.id,
                business_name=t.business_name,
                contact_email=t.contact_email,
                plan_key=plan_key,
                plan_name=plan_name,
                status=t.status.value,
                subscription_ends_at=t.subscription_ends_at.isoformat()
                if t.subscription_ends_at
                else None,
                owner_phone_e164=owner.phone_e164 if owner else None,
                owner_name=owner.full_name if owner else None,
                product_count=prod_count.get(t.id, 0),
                order_count=ord_count.get(t.id, 0),
                last_message_at=last_m.isoformat() if last_m is not None else None,
            )
        )
    return out
