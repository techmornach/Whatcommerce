from pydantic import BaseModel, Field


class InboundWhatsAppMessage(BaseModel):
    tenant_id: str = Field(..., description="Tenant this WA session belongs to")
    message_id: str
    from_id: str = Field(..., description="WhatsApp JID, e.g. 234...@c.us")
    from_me: bool = False
    body: str = ""
    timestamp: int | None = None
    chat_id: str | None = None


class OutboundWhatsAppMessage(BaseModel):
    to: str = Field(..., description="WhatsApp JID")
    body: str


class InboundAck(BaseModel):
    """Response to the bridge after handling a message (stub agent)."""

    replies: list[OutboundWhatsAppMessage] = Field(default_factory=list)
