"""Route inbound store-manager WhatsApp traffic to the correct tenant (one worker = one tenant)."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.tenant import Tenant
from app.utils.phone import normalize_phone_e164
from app.services.store_manager_agent import run_store_manager_agent


async def handle_store_manager_inbound(
    db: AsyncSession,
    *,
    tenant_hint: Optional[str],
    customer_phone_e164: str,
    text: str,
) -> list[str]:
    """
    Each store-manager Node process must set TENANT_ID in its .env.
    That ties this WhatsApp session to exactly one row in `tenants`, so many stores never share context.
    """
    if not tenant_hint or not tenant_hint.strip():
        return [
            "This store bot is missing TENANT_ID in its worker .env. "
            "Each shop should run its own process with its own tenant UUID."
        ]
    try:
        tid = UUID(tenant_hint.strip())
    except ValueError:
        return ["TENANT_ID on the worker is not a valid UUID."]

    tenant = await db.get(Tenant, tid)
    if tenant is None:
        return ["No shop found for this TENANT_ID. Check the worker configuration."]

    settings = get_settings()
    if settings.openai_api_key:
        try:
            replies = await run_store_manager_agent(
                db=db,
                tenant_id=tid,
                sender_phone_e164=normalize_phone_e164(customer_phone_e164),
                user_message=text or "Hello",
            )
            await db.commit()
            return replies
        except Exception:
            await db.rollback()
            return ["The store assistant hit an error. Try again shortly."]

    who = customer_phone_e164
    await db.commit()
    return [
        f"You're messaging *{tenant.business_name}* (store manager linked). "
        f"We received your note from {who}. Set OPENAI_API_KEY on the API for AI + catalog tools."
    ]
