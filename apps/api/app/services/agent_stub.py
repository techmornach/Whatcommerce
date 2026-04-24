from app.schemas.whatsapp import InboundWhatsAppMessage, InboundAck, OutboundWhatsAppMessage


def run_stub_agent(msg: InboundWhatsAppMessage) -> InboundAck:
    """
    Placeholder until the real OpenAI agent exists.
    Echoes inbound text for staff smoke tests; ignores automated/from_me.
    """
    if msg.from_me:
        return InboundAck(replies=[])

    text = (msg.body or "").strip()
    if not text:
        return InboundAck(replies=[])

    reply = f"[Whatcommerce stub] You said: {text[:500]}"
    return InboundAck(replies=[OutboundWhatsAppMessage(to=msg.from_id, body=reply)])
