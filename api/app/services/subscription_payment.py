from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import subscription_amount_kobo
from app.models.tenant import Tenant
from app.services.paystack import build_payment_reference, initialize_transaction


async def start_paystack_subscription_checkout(
    db: AsyncSession,
    tenant: Tenant,
    customer_email: str,
) -> dict[str, Any]:
    """Call Paystack initialize and persist `last_paystack_reference`. Caller should commit."""
    amount_kobo = await subscription_amount_kobo(db, tenant.plan_tier, tenant.billing_period)
    reference = build_payment_reference(str(tenant.id))
    metadata = {"tenant_id": str(tenant.id)}
    out = await initialize_transaction(
        email=customer_email,
        amount_kobo=amount_kobo,
        reference=reference,
        metadata=metadata,
    )
    data = out.get("data") or {}
    tenant.last_paystack_reference = reference
    await db.flush()
    return {
        "authorization_url": data.get("authorization_url"),
        "access_code": data.get("access_code"),
        "reference": data.get("reference") or reference,
        "amount_kobo": amount_kobo,
    }
