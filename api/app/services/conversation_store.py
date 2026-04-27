import logging
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConversationEvent

logger = logging.getLogger(__name__)


def append_event(
    db: Session,
    *,
    wa_chat_id: str,
    phone_e164: str,
    tenant_id: int | None,
    user_id: int | None,
    role: str,
    kind: str,
    content: str,
    event_metadata: dict | None = None,
) -> ConversationEvent:
    ev = ConversationEvent(
        wa_chat_id=wa_chat_id,
        phone_e164=phone_e164,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        kind=kind,
        content=content,
        event_metadata=event_metadata,
    )
    db.add(ev)
    db.flush()
    return ev


def load_openai_messages(
    db: Session, *, phone_e164: str, tenant_id: int | None, limit: int = 32
) -> list[dict[str, str]]:
    q = select(ConversationEvent).where(ConversationEvent.phone_e164 == phone_e164)
    if tenant_id is None:
        q = q.where(ConversationEvent.tenant_id.is_(None))
    else:
        q = q.where(ConversationEvent.tenant_id == tenant_id)
    q = q.where(ConversationEvent.role.in_(("user", "assistant")))
    q = q.order_by(ConversationEvent.id.desc()).limit(max(1, min(limit, 64)))
    rows: Sequence[ConversationEvent] = list(db.execute(q).scalars().all())
    rows = list(reversed(rows))
    out: list[dict[str, str]] = []
    for r in rows:
        c = (r.content or "").strip()
        if not c:
            continue
        if r.role not in ("user", "assistant"):
            continue
        out.append({"role": r.role, "content": c})
    return out
