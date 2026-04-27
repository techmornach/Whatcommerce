"""
Send WhatsApp messages from the API by calling the Node bridge dispatch server.
"""

import logging

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ConversationEvent

logger = logging.getLogger(__name__)


def phone_e164_to_wa_chat_id(phone_e164: str) -> str:
    d = "".join(c for c in (phone_e164 or "") if c.isdigit())
    if not d:
        return ""
    return f"{d}@c.us"


def resolve_outbound_wa_chat_id(db: Session, phone_e164: str) -> str:
    """
    Prefer the last private chat id we saw for this user (e.g. …@lid). WhatsApp Web
    often rejects sendMessage(…@c.us) with 'No LID for user' when the session uses LID.
    Fall back to digits@c.us if we have no events.
    """
    row = (
        db.execute(
            select(ConversationEvent.wa_chat_id)
            .where(ConversationEvent.phone_e164 == phone_e164)
            .where(
                or_(
                    ConversationEvent.wa_chat_id.endswith("@c.us"),
                    ConversationEvent.wa_chat_id.endswith("@lid"),
                )
            )
            .order_by(ConversationEvent.id.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    if row and row.strip():
        return row.strip()
    return phone_e164_to_wa_chat_id(phone_e164)


def send_whatsapp_text(*, db: Session, phone_e164: str, text: str) -> None:
    """Best-effort outbound via the Node bridge; no-op if dispatch URL is unset."""
    settings = get_settings()
    url = (settings.whatsapp_bridge_dispatch_url or "").strip()
    if not url:
        logger.info(
            "WHATSAPP_BRIDGE_DISPATCH_URL not set; skip outbound WhatsApp to %s",
            phone_e164,
        )
        return
    chat_id = resolve_outbound_wa_chat_id(db, phone_e164)
    if not chat_id:
        logger.warning("Cannot build wa chat id from %s", phone_e164)
        return
    payload = {"chat_id": chat_id, "text": text}
    headers = {"X-Internal-Key": settings.internal_api_key}
    with httpx.Client(timeout=15.0) as client:
        r = client.post(url, json=payload, headers=headers)
    if r.status_code >= 400:
        # Bridge returns JSON { "error": "..." } on 4xx/5xx — log for debugging.
        detail = (r.text or "")[:2000]
        logger.error(
            "WhatsApp dispatch HTTP %s to %s (chat_id=%s): %s",
            r.status_code,
            url,
            chat_id,
            detail,
        )
    r.raise_for_status()
    logger.info("Outbound WhatsApp sent to %s", chat_id[:20])


def send_whatsapp_text_best_effort(*, db: Session, phone_e164: str, text: str) -> bool:
    """Like send_whatsapp_text but never raises (e.g. guard alert to admin)."""
    try:
        send_whatsapp_text(db=db, phone_e164=phone_e164, text=text)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("WhatsApp best-effort send failed to %s: %s", phone_e164, e)
        return False


def notify_user_payment_confirmed(
    *, db: Session, phone_e164: str, text: str
) -> None:
    send_whatsapp_text(db=db, phone_e164=phone_e164, text=text)


def notify_user_payment_failed(*, db: Session, phone_e164: str, text: str) -> None:
    send_whatsapp_text(db=db, phone_e164=phone_e164, text=text)
