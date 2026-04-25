from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_internal_secret
from app.db.session import get_db
from app.services.onboarding_fsm import handle_whatcommerce_inbound
from app.services.store_manager_inbound import handle_store_manager_inbound
from app.services.serper import serper_search

router = APIRouter(prefix="/v1/internal", tags=["internal"], dependencies=[Depends(require_internal_secret)])


class SerperSearchBody(BaseModel):
    q: str = Field(min_length=1, max_length=500)
    num: int = Field(default=8, ge=1, le=20)


@router.post("/serper/search")
async def internal_serper_search(body: SerperSearchBody) -> dict[str, Any]:
    try:
        return await serper_search(body.q, num=body.num)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


class WhatsAppInboundBody(BaseModel):
    channel: Literal["whatcommerce", "store_manager"]
    from_e164: str = Field(..., min_length=5, max_length=32)
    text: str = Field(default="", max_length=8000)
    tenant_hint: Optional[str] = Field(default=None, max_length=64)


@router.post("/whatsapp/inbound")
async def whatsapp_inbound(body: WhatsAppInboundBody, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Receive normalized messages from the Node whatsapp-web.js worker."""
    if body.channel == "whatcommerce":
        replies = await handle_whatcommerce_inbound(db, body.from_e164, body.text)
    else:
        replies = await handle_store_manager_inbound(
            db,
            tenant_hint=body.tenant_hint,
            customer_phone_e164=body.from_e164,
            text=body.text,
        )
    return {"replies": replies, "channel": body.channel, "from_e164": body.from_e164}
