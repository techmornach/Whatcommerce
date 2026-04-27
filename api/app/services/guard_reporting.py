from __future__ import annotations

import logging
import re
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSetting, Tenant, User
from app.services.whatsapp_outbound import send_whatsapp_text_best_effort

logger = logging.getLogger(__name__)

KEY_GUARD_REPORT_E164 = "guard_report_whatsapp_e164"
_MAX_MSG = 3500
_MAX_CHUNK = 3800

GuardKind = Literal["input", "output"]
FlowKind = Literal["onboarding", "store"]


def get_guard_report_destination_e164(db: Session) -> str | None:
    row = (
        db.execute(
            select(PlatformSetting).where(PlatformSetting.key == KEY_GUARD_REPORT_E164)
        )
        .scalars()
        .first()
    )
    if not row or not (row.value or "").strip():
        return None
    raw = (row.value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10:
        return None
    if raw.strip().startswith("+"):
        return f"+{digits}"
    return f"+{digits}"


def describe_registered_user_line(db: Session, phone_e164: str) -> str:
    u = (
        db.execute(select(User).where(User.phone_e164 == phone_e164))
        .scalars()
        .first()
    )
    if u is None:
        return "No — phone not registered as a user in the database."
    parts = [f"Yes — user id *{u.id}*"]
    if u.tenant_id is not None:
        t = db.get(Tenant, u.tenant_id)
        if t is not None:
            parts.append(f'tenant *{t.business_name}* (id {t.id})')
        else:
            parts.append(f"tenant_id {u.tenant_id} (row missing)")
    else:
        parts.append("no tenant linked (e.g. still onboarding)")
    if u.full_name and str(u.full_name).strip():
        parts.append(f"name: *{u.full_name.strip()[:80]}*")
    return " | ".join(parts)


def _split_whatsapp_chunks(text: str, max_len: int) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    if len(t) <= max_len:
        return [t]
    chunks: list[str] = []
    rest = t
    while rest:
        if len(rest) <= max_len:
            chunks.append(rest)
            break
        cut = rest.rfind("\n\n", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        chunks.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    return [c for c in chunks if c]


def report_guard_block(
    db: Session,
    *,
    kind: GuardKind,
    flow: FlowKind,
    phone_e164: str,
    latest_user_message: str,
    context_excerpt: str,
    category: str | None,
    blocked_content_summary: str,
) -> None:
    dest = get_guard_report_destination_e164(db)
    if not dest:
        return
    user_line = describe_registered_user_line(db, phone_e164)
    cat = (category or "").strip() or "unspecified"
    kind_label = "Input guard (inbound)" if kind == "input" else "Output guard (outbound)"
    flow_label = "Onboarding" if flow == "onboarding" else "Store manager"
    umsg = (latest_user_message or "").strip() or "(empty)"
    if len(umsg) > _MAX_MSG:
        umsg = umsg[:_MAX_MSG] + "…"
    ctx = (context_excerpt or "").strip() or "(none)"
    if len(ctx) > _MAX_MSG:
        ctx = ctx[:_MAX_MSG] + "…"
    block_blob = (blocked_content_summary or "").strip() or "(n/a)"
    if len(block_blob) > _MAX_MSG:
        block_blob = block_blob[:_MAX_MSG] + "…"

    body = (
        f"*Whatcommerce — guard alert*\n\n"
        f"*Guard:* {kind_label}\n"
        f"*Flow:* {flow_label}\n"
        f"*User phone:* {phone_e164}\n"
        f"*Known user?* {user_line}\n"
        f"*Category / reason code:* {cat}\n\n"
        f"*Latest user message:*\n{umsg}\n\n"
        f"*Context (excerpt):*\n{ctx}\n\n"
        f"*What was flagged (detail):*\n{block_blob}"
    )
    chunks = _split_whatsapp_chunks(body, _MAX_CHUNK)
    for i, ch in enumerate(chunks):
        part = ch if len(chunks) == 1 else f"({i + 1}/{len(chunks)})\n{ch}"
        ok = send_whatsapp_text_best_effort(db=db, phone_e164=dest, text=part)
        if not ok and i == 0:
            logger.warning("guard report: failed to send to %s", dest)
            break
