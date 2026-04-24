import httpx

from app.config import settings
from app.schemas.whatsapp import OutboundWhatsAppMessage


async def send_via_bridge(messages: list[OutboundWhatsAppMessage]) -> None:
    if not messages:
        return
    url = f"{settings.bridge_base_url.rstrip('/')}/internal/send"
    payload = {"messages": [m.model_dump() for m in messages]}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            json=payload,
            headers={"X-Internal-Token": settings.internal_secret},
        )
        r.raise_for_status()
