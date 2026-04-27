from sqlalchemy.orm import Session

from app.services.onboarding_agent import run_onboarding_agent
from app.utils.phone import wa_chat_id_to_phone_e164


def process_inbound_onboarding(
    db: Session, *, wa_chat_id: str, body: str
) -> list[str]:
    text = (body or "").strip()
    if _is_group(wa_chat_id):
        return [
            "Please open a private chat with this number to register and "
            "manage your store."
        ]
    if not text:
        return ["Please send a text message to continue."]

    phone = wa_chat_id_to_phone_e164(wa_chat_id)
    if not phone or len(phone) < 10:
        return [
            "Could not read your phone number from this chat. Try again from your phone."
        ]
    return run_onboarding_agent(db, wa_chat_id=wa_chat_id, phone_e164=phone)


def _is_group(wa_chat_id: str) -> bool:
    return wa_chat_id.endswith("@g.us")
