from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_PLATFORM_SETTINGS_ID
from app.models.billing_plan import BillingPlan
from app.models.platform import PlatformSettings


async def ensure_default_platform_settings(session: AsyncSession) -> None:
    result = await session.execute(
        select(PlatformSettings).where(PlatformSettings.id == DEFAULT_PLATFORM_SETTINGS_ID)
    )
    if result.scalar_one_or_none() is None:
        session.add(
            PlatformSettings(
                id=DEFAULT_PLATFORM_SETTINGS_ID,
                landing_whatsapp_e164=None,
                knowledge_base_text=None,
                whatcommerce_session_phone_e164=None,
                whatcommerce_session_ready_at=None,
                whatcommerce_pending_session_reset=False,
            )
        )
        await session.commit()


async def ensure_default_billing_plans(session: AsyncSession) -> None:
    """Seed baseline plans if the table is empty."""
    r = await session.execute(select(BillingPlan.tier).limit(1))
    if r.scalar_one_or_none() is not None:
        return
    session.add_all(
        [
            BillingPlan(
                tier="lite",
                monthly_amount_ngn=5_000,
                yearly_amount_ngn=5_000 * 12,
                max_products=50,
                max_users=2,
                is_active=True,
            ),
            BillingPlan(
                tier="standard",
                monthly_amount_ngn=10_000,
                yearly_amount_ngn=10_000 * 12,
                max_products=100,
                max_users=3,
                is_active=True,
            ),
            BillingPlan(
                tier="premium",
                monthly_amount_ngn=20_000,
                yearly_amount_ngn=20_000 * 12,
                max_products=500,
                max_users=5,
                is_active=True,
            ),
        ]
    )
    await session.commit()
