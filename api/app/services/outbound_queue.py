"""WhatsApp outbound queue: claim/ack, stale reclaim, dead letters, owner notifications."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import delete, func as sqlfunc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import Order
from app.models.tenant import Tenant
from app.models.whatsapp_outbound import WhatsappOutboundMessage
from app.utils.phone import normalize_phone_e164

WorkerChannel = Literal["whatcommerce", "store_manager"]

STALE_MINUTES = int(os.getenv("WHATSAPP_OUTBOUND_STALE_MINUTES", "10"))
MAX_ATTEMPTS = int(os.getenv("WHATSAPP_OUTBOUND_MAX_ATTEMPTS", "5"))


def _append_err(prev: str | None, msg: str) -> str:
    p = (prev or "").strip()
    if not p:
        return msg[:4000]
    return f"{p}\n{msg}"[:4000]


async def _reclaim_stale_sending(
    db: AsyncSession,
    *,
    worker_channel: WorkerChannel,
    tenant_id: UUID | None,
) -> None:
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)
    q = select(WhatsappOutboundMessage).where(
        WhatsappOutboundMessage.status == "sending",
        WhatsappOutboundMessage.updated_at < stale_before,
        WhatsappOutboundMessage.worker_channel == worker_channel,
    )
    if tenant_id is not None:
        q = q.where(WhatsappOutboundMessage.tenant_id == tenant_id)
    res = await db.execute(q)
    rows = res.scalars().all()
    now = datetime.now(timezone.utc)
    for r in rows:
        new_attempt = int(r.attempt_count or 0) + 1
        r.last_error = _append_err(r.last_error, "stale_sending_timeout")
        if new_attempt >= MAX_ATTEMPTS:
            r.status = "dead_letter"
            r.attempt_count = new_attempt
            r.failure_class = "stale_max"
            r.dead_letter_at = now
        else:
            r.status = "pending"
            r.attempt_count = new_attempt
            r.failure_class = "stale"
    await db.flush()


async def claim_outbound(
    db: AsyncSession,
    *,
    worker_channel: WorkerChannel,
    tenant_id: UUID | None,
    limit: int,
) -> list[dict[str, Any]]:
    await _reclaim_stale_sending(db, worker_channel=worker_channel, tenant_id=tenant_id)

    stmt = (
        select(WhatsappOutboundMessage)
        .where(
            WhatsappOutboundMessage.worker_channel == worker_channel,
            WhatsappOutboundMessage.status == "pending",
            WhatsappOutboundMessage.attempt_count < MAX_ATTEMPTS,
        )
        .order_by(WhatsappOutboundMessage.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    if tenant_id is not None:
        stmt = stmt.where(WhatsappOutboundMessage.tenant_id == tenant_id)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    for r in rows:
        r.status = "sending"
    await db.flush()

    return [
        {"id": str(r.id), "tenant_id": str(r.tenant_id), "to_phone_e164": r.to_phone_e164, "body": r.body}
        for r in rows
    ]


async def ack_outbound_sent(
    db: AsyncSession,
    *,
    worker_channel: WorkerChannel,
    tenant_id: UUID | None,
    ids: list[UUID],
) -> int:
    stmt = delete(WhatsappOutboundMessage).where(
        WhatsappOutboundMessage.worker_channel == worker_channel,
        WhatsappOutboundMessage.id.in_(ids),
        WhatsappOutboundMessage.status == "sending",
    )
    if tenant_id is not None:
        stmt = stmt.where(WhatsappOutboundMessage.tenant_id == tenant_id)
    res = await db.execute(stmt)
    return int(res.rowcount or 0)


async def report_outbound_failure(
    db: AsyncSession,
    *,
    worker_channel: WorkerChannel,
    tenant_id: UUID | None,
    ids: list[UUID],
    error: str,
    failure_class: str,
) -> dict[str, int]:
    """After sendMessage fails or ack repeatedly fails (treat as delivery failure)."""
    q = select(WhatsappOutboundMessage).where(
        WhatsappOutboundMessage.worker_channel == worker_channel,
        WhatsappOutboundMessage.id.in_(ids),
        WhatsappOutboundMessage.status == "sending",
    )
    if tenant_id is not None:
        q = q.where(WhatsappOutboundMessage.tenant_id == tenant_id)
    res = await db.execute(q)
    rows = res.scalars().all()
    now = datetime.now(timezone.utc)
    dead = 0
    retried = 0
    err = (error or "unknown")[:2000]
    for r in rows:
        new_attempt = int(r.attempt_count or 0) + 1
        r.last_error = _append_err(r.last_error, err)
        r.failure_class = failure_class[:32] if failure_class else "send"
        if new_attempt >= MAX_ATTEMPTS:
            r.status = "dead_letter"
            r.attempt_count = new_attempt
            r.dead_letter_at = now
            dead += 1
        else:
            r.status = "pending"
            r.attempt_count = new_attempt
            retried += 1
    await db.flush()
    return {"dead_letter": dead, "returned_pending": retried}


async def forgive_outbound_after_send(
    db: AsyncSession,
    *,
    worker_channel: WorkerChannel,
    tenant_id: UUID | None,
    ids: list[UUID],
) -> int:
    """
    Delete rows stuck in `sending` after WhatsApp accepted the message but API ack could not be confirmed.
    Prevents duplicate user messages when stale reclaim would otherwise retry.
    """
    stmt = delete(WhatsappOutboundMessage).where(
        WhatsappOutboundMessage.worker_channel == worker_channel,
        WhatsappOutboundMessage.id.in_(ids),
        WhatsappOutboundMessage.status == "sending",
    )
    if tenant_id is not None:
        stmt = stmt.where(WhatsappOutboundMessage.tenant_id == tenant_id)
    res = await db.execute(stmt)
    return int(res.rowcount or 0)


async def outbound_metrics(db: AsyncSession, *, since_hours: int = 24) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(hours=max(1, min(since_hours, 168)))
    r1 = await db.execute(
        select(WhatsappOutboundMessage.status, sqlfunc.count())
        .select_from(WhatsappOutboundMessage)
        .group_by(WhatsappOutboundMessage.status)
    )
    by_status = {str(row[0]): int(row[1]) for row in r1.all()}
    r2 = await db.execute(
        select(
            WhatsappOutboundMessage.worker_channel,
            WhatsappOutboundMessage.status,
            sqlfunc.count(),
        )
        .select_from(WhatsappOutboundMessage)
        .group_by(WhatsappOutboundMessage.worker_channel, WhatsappOutboundMessage.status)
    )
    by_channel_status = r2.all()
    dead_recent = await db.scalar(
        select(sqlfunc.count()).select_from(WhatsappOutboundMessage).where(
            WhatsappOutboundMessage.status == "dead_letter",
            WhatsappOutboundMessage.dead_letter_at.isnot(None),
            WhatsappOutboundMessage.dead_letter_at >= since,
        )
    )
    pending_stuck = await db.scalar(
        select(sqlfunc.count()).select_from(WhatsappOutboundMessage).where(
            WhatsappOutboundMessage.status == "pending",
            WhatsappOutboundMessage.attempt_count >= MAX_ATTEMPTS,
        )
    )
    return {
        "by_status": {str(k): int(v) for k, v in by_status},
        "by_channel_status": [[str(a), str(b), int(c)] for a, b, c in by_channel_status],
        "dead_letter_since_cutoff": int(dead_recent or 0),
        "pending_over_attempt_budget": int(pending_stuck or 0),
        "cutoff_hours": since_hours,
        "stale_minutes": STALE_MINUTES,
        "max_attempts": MAX_ATTEMPTS,
    }


async def enqueue_owner_pending_order_notification(
    db: AsyncSession,
    *,
    tenant: Tenant,
    order: Order,
) -> None:
    """Notify the shop owner on the platform WhatsApp session (not the business line)."""
    owner = normalize_phone_e164(tenant.onboarding_phone_e164)
    if len(owner) < 10:
        return
    lines = [
        f"*{tenant.business_name}*: new order pending confirmation.",
        f"Order id: `{order.id}`",
        f"Customer: {order.customer_name} ({order.customer_phone_e164})",
    ]
    if order.order_summary:
        summ = order.order_summary.replace("\n", " ").strip()[:400]
        lines.append(f"Items / notes: {summ}")
    lines.append("Reply on your *store business WhatsApp* to confirm or reject (owner number only).")
    body = "\n".join(lines)[:3500]
    db.add(
        WhatsappOutboundMessage(
            tenant_id=tenant.id,
            to_phone_e164=owner,
            body=body,
            status="pending",
            worker_channel="whatcommerce",
            attempt_count=0,
        )
    )
    await db.flush()
