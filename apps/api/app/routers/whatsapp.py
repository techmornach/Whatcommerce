from fastapi import APIRouter, Depends

from app.deps.internal_auth import require_internal_secret
from app.schemas.whatsapp import InboundAck, InboundWhatsAppMessage
from app.services.agent_stub import run_stub_agent
from app.services.bridge_client import send_via_bridge

router = APIRouter(prefix="/internal/whatsapp", tags=["internal-whatsapp"])


@router.post("/inbound", dependencies=[Depends(require_internal_secret)])
async def inbound_message(payload: InboundWhatsAppMessage) -> InboundAck:
    """
    Called by the WA bridge when a message arrives for a tenant session.
    Runs stub agent then pushes replies through the bridge HTTP API.
    """
    ack = run_stub_agent(payload)
    await send_via_bridge(ack.replies)
    return ack
