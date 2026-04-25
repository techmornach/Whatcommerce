"""OpenAI Agents SDK + product/order tools for the store-manager WhatsApp worker."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from uuid import UUID

from agents import Agent, Runner, RunContextWrapper, function_tool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import max_products_for_tier
from app.core.config import get_settings
from app.models.commerce import Order, OrderStatus, Product
from app.models.customer import Customer
from app.models.tenant import Tenant
from app.services.outbound_queue import enqueue_owner_pending_order_notification
from app.utils.phone import normalize_phone_e164

logger = logging.getLogger(__name__)


@dataclass
class StoreManagerContext:
    db: AsyncSession
    tenant_id: UUID
    sender_phone_e164: str


def _chunk_reply(text: str, limit: int = 3500) -> list[str]:
    text = (text or "").strip()
    if not text:
        return ["(empty response)"]
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def _is_shop_owner(tenant: Tenant | None, sender: str) -> bool:
    if tenant is None:
        return False
    return normalize_phone_e164(tenant.onboarding_phone_e164) == normalize_phone_e164(sender)


@function_tool
async def list_products(ctx: RunContextWrapper[StoreManagerContext]) -> str:
    """List up to 40 products for this store (name, price in NGN, id)."""
    c = ctx.context
    r = await c.db.execute(
        select(Product)
        .where(Product.tenant_id == c.tenant_id)
        .order_by(Product.created_at.desc())
        .limit(40)
    )
    rows = r.scalars().all()
    if not rows:
        return "No products yet."
    lines = [f"{p.name} — ₦{p.price_minor:,} (id {p.id})" for p in rows]
    return "\n".join(lines)


@function_tool
async def add_product(
    ctx: RunContextWrapper[StoreManagerContext],
    name: str,
    price_ngn: int,
    description: str = "",
) -> str:
    """Add a product. price_ngn is whole naira (e.g. 2500). Respects plan product limits."""
    c = ctx.context
    tenant = await c.db.get(Tenant, c.tenant_id)
    if not tenant:
        return "Tenant not found."
    cap = await max_products_for_tier(c.db, tenant.plan_tier)
    cnt = await c.db.scalar(select(func.count()).select_from(Product).where(Product.tenant_id == c.tenant_id))
    if int(cnt or 0) >= cap:
        return f"Product limit reached ({cap} for current plan)."
    nm = (name or "").strip()
    if len(nm) < 1:
        return "Product name required."
    if price_ngn < 0:
        return "Invalid price."
    desc = (description or "").strip()
    p = Product(
        tenant_id=c.tenant_id,
        name=nm[:255],
        description=desc[:4000] if desc else None,
        price_minor=int(price_ngn),
        currency="NGN",
    )
    c.db.add(p)
    await c.db.flush()
    return f"Added product {p.name} at ₦{p.price_minor:,} (id {p.id})."


@function_tool
async def list_orders(ctx: RunContextWrapper[StoreManagerContext]) -> str:
    """List recent orders (status, customer, id)."""
    c = ctx.context
    r = await c.db.execute(
        select(Order)
        .where(Order.tenant_id == c.tenant_id)
        .order_by(Order.created_at.desc())
        .limit(25)
    )
    rows = r.scalars().all()
    if not rows:
        return "No orders yet."
    lines = [
        f"{o.id} | {o.status} | {o.customer_name} | {o.customer_phone_e164}" for o in rows
    ]
    return "\n".join(lines)


@function_tool
async def list_pending_orders(ctx: RunContextWrapper[StoreManagerContext]) -> str:
    """List orders waiting for merchant confirmation."""
    c = ctx.context
    r = await c.db.execute(
        select(Order)
        .where(
            Order.tenant_id == c.tenant_id,
            Order.status == OrderStatus.pending_confirmation.value,
        )
        .order_by(Order.created_at.asc())
        .limit(30)
    )
    rows = r.scalars().all()
    if not rows:
        return "No pending orders."
    lines = []
    for o in rows:
        extra = (o.order_summary or "").replace("\n", " ")[:120]
        lines.append(f"{o.id} | {o.customer_name} | {o.customer_phone_e164} | {extra}")
    return "\n".join(lines)


@function_tool
async def submit_customer_order(
    ctx: RunContextWrapper[StoreManagerContext],
    customer_name: str,
    customer_phone: str,
    shipping_address: str,
    items_summary: str = "",
) -> str:
    """Create an order in pending_confirmation. customer_phone should be digits (E.164 without +)."""
    c = ctx.context
    phone = normalize_phone_e164(customer_phone)
    if len(phone) < 10:
        return "Invalid customer_phone."
    nm = (customer_name or "").strip()
    if len(nm) < 2:
        return "Customer name required."
    addr = (shipping_address or "").strip()
    if len(addr) < 5:
        return "Shipping address required."
    summ = (items_summary or "").strip()
    tenant = await c.db.get(Tenant, c.tenant_id)
    if tenant and phone == normalize_phone_e164(tenant.onboarding_phone_e164):
        return "Use a customer phone that is not the shop owner's onboarding number."
    o = Order(
        tenant_id=c.tenant_id,
        customer_phone_e164=phone,
        customer_name=nm[:255],
        shipping_address=addr[:8000],
        order_summary=summ[:8000] if summ else None,
        status=OrderStatus.pending_confirmation.value,
    )
    c.db.add(o)
    await c.db.flush()
    if tenant:
        await enqueue_owner_pending_order_notification(c.db, tenant=tenant, order=o)
    return f"Order {o.id} created — pending merchant confirmation. Ask the owner to confirm in chat."


@function_tool
async def confirm_order(ctx: RunContextWrapper[StoreManagerContext], order_id: str) -> str:
    """Confirm a pending order (shop owner only — same phone as platform onboarding)."""
    c = ctx.context
    tenant = await c.db.get(Tenant, c.tenant_id)
    if not _is_shop_owner(tenant, c.sender_phone_e164):
        return "Only the shop owner (onboarding WhatsApp number) can confirm orders."
    try:
        oid = UUID(order_id.strip())
    except ValueError:
        return "Invalid order_id (must be UUID)."
    o = await c.db.get(Order, oid)
    if o is None or o.tenant_id != c.tenant_id:
        return "Order not found."
    if o.status != OrderStatus.pending_confirmation.value:
        return f"Order is not pending (status={o.status})."
    o.status = OrderStatus.confirmed.value
    o.rejection_reason = None
    existing = await c.db.execute(
        select(Customer).where(
            Customer.tenant_id == c.tenant_id,
            Customer.phone_e164 == o.customer_phone_e164,
        )
    )
    if existing.scalars().first() is None:
        c.db.add(
            Customer(
                tenant_id=c.tenant_id,
                phone_e164=o.customer_phone_e164,
                display_name=o.customer_name,
            )
        )
    await c.db.flush()
    return f"Order {o.id} confirmed."


@function_tool
async def reject_order(ctx: RunContextWrapper[StoreManagerContext], order_id: str, reason: str = "") -> str:
    """Reject a pending order (shop owner only)."""
    c = ctx.context
    tenant = await c.db.get(Tenant, c.tenant_id)
    if not _is_shop_owner(tenant, c.sender_phone_e164):
        return "Only the shop owner can reject orders."
    try:
        oid = UUID(order_id.strip())
    except ValueError:
        return "Invalid order_id."
    o = await c.db.get(Order, oid)
    if o is None or o.tenant_id != c.tenant_id:
        return "Order not found."
    if o.status != OrderStatus.pending_confirmation.value:
        return f"Order is not pending (status={o.status})."
    o.status = OrderStatus.rejected.value
    o.rejection_reason = (reason or "").strip()[:4000] or None
    await c.db.flush()
    return f"Order {o.id} rejected."


_STORE_INSTRUCTIONS = """You are the WhatsApp store assistant for ONE shop (the tenant).
You can list/add products, list orders, and handle customer orders.
Prices are in Nigerian Naira (whole naira for add_product).

Orders:
- Use submit_customer_order when a shopper gives name, phone, address, and what they want.
- Pending orders must be confirmed or rejected by the shop owner (the same phone they used for Whatcommerce onboarding). Use list_pending_orders, confirm_order, reject_order for the owner.
- Be brief. Do not invent Paystack or payment confirmations.
"""


async def run_store_manager_agent(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    sender_phone_e164: str,
    user_message: str,
) -> list[str]:
    settings = get_settings()
    if not settings.openai_api_key:
        return ["AI is not configured on the server (OPENAI_API_KEY)."]
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return ["Store not found."]

    tools = [
        list_products,
        add_product,
        list_orders,
        list_pending_orders,
        submit_customer_order,
        confirm_order,
        reject_order,
    ]

    agent = Agent[StoreManagerContext](
        name="store_manager",
        instructions=_STORE_INSTRUCTIONS + f"\nStore name: {tenant.business_name}\n",
        tools=tools,
        model=settings.openai_model,
    )
    ctx = StoreManagerContext(
        db=db,
        tenant_id=tenant_id,
        sender_phone_e164=normalize_phone_e164(sender_phone_e164),
    )
    try:
        result = await Runner.run(agent, input=user_message.strip(), context=ctx, max_turns=16)
    except Exception:
        logger.exception("store manager agent failed")
        return ["Sorry, something went wrong. Try again shortly."]
    out = result.final_output
    text = out if isinstance(out, str) else str(out)
    return _chunk_reply(text)
