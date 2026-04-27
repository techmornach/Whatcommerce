import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ConversationEvent, User
from app.services.conversation_store import append_event
from app.services.media_ingest import normalize_inbound
from app.services.onboarding_fsm import process_inbound_onboarding
from app.services.product_image_storage import public_url_for_path, save_product_image
from app.services.store_context import resolve_store_context
from app.services.store_manager_agent import run_store_manager
from app.utils.phone import wa_chat_id_to_phone_e164

logger = logging.getLogger(__name__)


def _maybe_append_stored_product_image_url(
    settings,
    text: str,
    *,
    ctx,
    kind: str,
    image_raw: bytes | None,
    ev_meta: dict,
) -> str:
    if ctx is None or kind != "image" or not image_raw:
        return text
    if ev_meta.get("caption_only"):
        return text
    try:
        path = save_product_image(
            settings,
            tenant_id=ctx.tenant_id,
            raw=image_raw,
            mimetype=ev_meta.get("mimetype"),
        )
        url = public_url_for_path(settings, path)
        ev_meta["stored_image_url"] = url
        return (
            f"{text}\n\n*Catalog image URL* (use in add_product / update_product "
            f"*image_urls*):\n{url}"
        )
    except OSError as e:
        logger.warning("product image save failed: %s", e)
        return text


def _is_group(wa_chat_id: str) -> bool:
    return wa_chat_id.endswith("@g.us")


def _user_id_for_phone(db: Session, phone_e164: str) -> int | None:
    u = (
        db.execute(select(User).where(User.phone_e164 == phone_e164))
        .scalars()
        .first()
    )
    return u.id if u is not None else None


def _append_assistant_transcript(
    db: Session,
    *,
    wa_chat_id: str,
    phone_e164: str,
    tenant_id: int | None,
    user_id: int | None,
    replies: list[str],
) -> None:
    text = "\n\n".join((r or "").strip() for r in replies if (r or "").strip())
    if not text:
        return
    append_event(
        db,
        wa_chat_id=wa_chat_id,
        phone_e164=phone_e164,
        tenant_id=tenant_id,
        user_id=user_id,
        role="assistant",
        kind="text",
        content=text,
        event_metadata=None,
    )


def _is_duplicate_inbound_message(
    db: Session, *, wa_chat_id: str, message_id: str | None
) -> bool:
    mid = (message_id or "").strip()
    if not mid:
        return False
    row = (
        db.execute(
            select(ConversationEvent.id).where(
                ConversationEvent.wa_chat_id == wa_chat_id,
                ConversationEvent.role == "user",
                ConversationEvent.event_metadata["message_id"].astext == mid,
            )
        )
        .first()
    )
    return row is not None


def process_inbound_whatsapp(
    db: Session,
    *,
    wa_chat_id: str,
    body: str,
    message_type: str | None = None,
    message_id: str | None = None,
    media_mimetype: str | None = None,
    media_base64: str | None = None,
) -> list[str]:
    settings = get_settings()
    if _is_group(wa_chat_id):
        return [
            "Please open a private chat with this number to register and manage your store."
        ]

    phone = wa_chat_id_to_phone_e164(wa_chat_id)
    if not phone or len(phone) < 10:
        return [
            "Could not read your phone number from this chat. Try again from your phone."
        ]

    if _is_duplicate_inbound_message(db, wa_chat_id=wa_chat_id, message_id=message_id):
        logger.info(
            "inbound dedupe: ignored duplicate message_id=%s chat=%s",
            message_id,
            wa_chat_id,
        )
        return []

    canonical, kind, ev_meta, image_raw = normalize_inbound(
        settings,
        body=body,
        message_type=message_type,
        media_mimetype=media_mimetype,
        media_base64=media_base64,
    )
    if message_id:
        ev_meta = {**ev_meta, "message_id": message_id}
    if ev_meta.get("empty") and not (canonical or "").strip():
        return [
            "Please send a *text* message, *voice* note, or *image* to continue."
        ]
    text = (canonical or "").strip()
    if not text:
        return [
            "Please send a *text* message, *voice* note, or *image* to continue."
        ]
    if ev_meta.get("router_short_circuit"):
        return [text]

    user_id = _user_id_for_phone(db, phone)
    ctx = resolve_store_context(db, phone)

    text = _maybe_append_stored_product_image_url(
        settings, text, ctx=ctx, kind=kind, image_raw=image_raw, ev_meta=ev_meta
    )

    if ctx is not None:
        append_event(
            db,
            wa_chat_id=wa_chat_id,
            phone_e164=phone,
            tenant_id=ctx.tenant_id,
            user_id=user_id,
            role="user",
            kind=kind,
            content=text,
            event_metadata=ev_meta,
        )
        replies = run_store_manager(db, ctx)
        _append_assistant_transcript(
            db,
            wa_chat_id=wa_chat_id,
            phone_e164=phone,
            tenant_id=ctx.tenant_id,
            user_id=user_id,
            replies=replies,
        )
        return replies

    append_event(
        db,
        wa_chat_id=wa_chat_id,
        phone_e164=phone,
        tenant_id=None,
        user_id=user_id,
        role="user",
        kind=kind,
        content=text,
        event_metadata=ev_meta,
    )
    replies = process_inbound_onboarding(db, wa_chat_id=wa_chat_id, body=text)
    _append_assistant_transcript(
        db,
        wa_chat_id=wa_chat_id,
        phone_e164=phone,
        tenant_id=None,
        user_id=user_id,
        replies=replies,
    )
    return replies
