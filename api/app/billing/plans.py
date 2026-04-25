"""DB-backed plan pricing/limits used by onboarding + billing + store-manager caps."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing_plan import BillingPlan


async def max_products_for_tier(db: AsyncSession, plan_tier: str) -> int:
    r = await db.execute(select(BillingPlan.max_products).where(BillingPlan.tier == plan_tier, BillingPlan.is_active))
    v = r.scalar_one_or_none()
    if v is not None:
        return int(v)
    # Safe fallback
    return 50


async def subscription_amount_ngn(db: AsyncSession, plan_tier: str, billing_period: str) -> int:
    r = await db.execute(
        select(BillingPlan.monthly_amount_ngn, BillingPlan.yearly_amount_ngn).where(
            BillingPlan.tier == plan_tier, BillingPlan.is_active
        )
    )
    row = r.first()
    if row is None:
        monthly = 5_000
        yearly = monthly * 12
    else:
        monthly = int(row[0])
        yearly = int(row[1]) if row[1] is not None else monthly * 12
    return yearly if billing_period == "yearly" else monthly


async def subscription_amount_kobo(db: AsyncSession, plan_tier: str, billing_period: str) -> int:
    return (await subscription_amount_ngn(db, plan_tier, billing_period)) * 100


def subscription_timedelta_days(billing_period: str) -> int:
    if billing_period == "yearly":
        return 365
    return 30


async def plan_choice_prompt(db: AsyncSession) -> str:
    """WhatsApp-friendly copy for plan selection (active plans)."""
    r = await db.execute(
        select(BillingPlan.tier, BillingPlan.monthly_amount_ngn, BillingPlan.max_products, BillingPlan.max_users)
        .where(BillingPlan.is_active)
        .order_by(BillingPlan.monthly_amount_ngn.asc())
    )
    rows = r.all()
    if not rows:
        rows = [
            ("lite", 5_000, 50, 2),
            ("standard", 10_000, 100, 3),
            ("premium", 20_000, 500, 5),
        ]
    lines = ["Choose a plan (reply with 1, 2, or 3):"]
    for i, (tier, monthly_ngn, max_products, max_users) in enumerate(rows[:3], start=1):
        label = str(tier).title()
        lines.append(f"{i}) {label} — ₦{int(monthly_ngn):,}/mo ({int(max_products)} products, {int(max_users)} users)")
    return "\n".join(lines)
