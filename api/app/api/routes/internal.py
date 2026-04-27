import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_internal_key
from app.db.session import get_db
from app.services.bridge_status import apply_bridge_report
from app.services.inbound_router import process_inbound_whatsapp

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
    dependencies=[Depends(require_internal_key)],
)


class InboundMessageIn(BaseModel):
    from_wa_id: str = Field(
        min_length=5, max_length=128, description="Chat id, e.g. 234...@c.us"
    )
    body: str = Field(min_length=0, max_length=32_000)
    message_id: str | None = None
    message_type: str | None = Field(default=None, max_length=64)
    media_mimetype: str | None = Field(default=None, max_length=256)
    media_base64: str | None = Field(default=None, max_length=10_485_760)


class InboundMessageOut(BaseModel):
    replies: list[str]


@router.post("/inbound-messages", response_model=InboundMessageOut)
def inbound_message(
    payload: InboundMessageIn,
    db: Session = Depends(get_db),
) -> InboundMessageOut:
    try:
        replies = process_inbound_whatsapp(
            db,
            wa_chat_id=payload.from_wa_id,
            body=payload.body,
            message_type=payload.message_type,
            message_id=payload.message_id,
            media_mimetype=payload.media_mimetype,
            media_base64=payload.media_base64,
        )
    except Exception as e:
        logger.exception("inbound_whatsapp: %s", e)
        return InboundMessageOut(
            replies=["Sorry, something went wrong. Please try again in a moment."]
        )
    return InboundMessageOut(replies=[r for r in replies if r])


@router.get("/ping")
def internal_ping() -> dict[str, str]:
    return {"status": "ok", "auth": "internal"}


class BridgeStateIn(BaseModel):
    status: str = Field(
        min_length=2,
        max_length=32,
        description="ready | qr | error | init",
    )
    message: str | None = Field(default=None, max_length=4_000)
    qr_data: str | None = Field(
        default=None,
        max_length=20_000,
        description="Raw QR payload from whatsapp-web.js (for admin to display)",
    )
    phone_e164: str | None = Field(
        default=None,
        max_length=32,
        description="Bot number in E.164; send when status=ready (not on every heartbeat)",
    )


@router.post("/bridge-status", response_model=dict)
def post_bridge_state(
    payload: BridgeStateIn,
    db: Session = Depends(get_db),
) -> dict:
    st = (payload.status or "").lower().strip()
    if st not in ("ready", "qr", "error", "init"):
        st = "error"
    apply_bridge_report(
        db,
        status=st,
        message=payload.message,
        qr_data=payload.qr_data,
        phone_e164=payload.phone_e164,
    )
    return {"ok": True, "status": st, "message": payload.message}
