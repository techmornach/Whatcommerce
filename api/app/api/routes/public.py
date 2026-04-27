import re
from urllib.parse import quote

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import PlatformSetting
from app.services.bridge_status import parse_public_bridge_state

router = APIRouter(prefix="/api/public", tags=["public"])


class PublicLandingConfig(BaseModel):
    whatsapp_e164: str
    whatsapp_href: str
    message_prefill: str
    bot_connected: bool
    link_state: str


@router.get("/config", response_model=PublicLandingConfig)
def get_public_landing_config(db: Session = Depends(get_db)) -> PublicLandingConfig:
    parsed = parse_public_bridge_state(db)
    st = (parsed.get("status") or "").lower()
    phone = (parsed.get("connected_e164") or "").strip()
    pre = _get_setting(
        db,
        "landing_message_prefill",
        "Hi! I'd like to get started with Whatcommerce.",
    )
    linked = st == "ready" and bool(phone)
    if st in ("qr", "init"):
        link_state = "pairing"
    elif linked:
        link_state = "linked"
    else:
        link_state = "unlinked"

    if not linked:
        return PublicLandingConfig(
            whatsapp_e164="",
            whatsapp_href="",
            message_prefill=pre,
            bot_connected=False,
            link_state=link_state,
        )

    digits = re.sub(r"\D", "", phone)
    if not digits and phone.startswith("+"):
        digits = re.sub(r"\D", "", phone[1:])
    number_path = digits or "0"
    href = f"https://wa.me/{number_path}" + (f"?text={quote(pre)}" if pre else "")
    return PublicLandingConfig(
        whatsapp_e164=phone if phone.startswith("+") else f"+{digits}",
        whatsapp_href=href,
        message_prefill=pre,
        bot_connected=True,
        link_state="linked",
    )


def _get_setting(db: Session, key: str, default: str) -> str:
    row = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalars().first()
    if row is None or not row.value:
        return default
    return row.value
