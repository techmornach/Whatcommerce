from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_internal_secret
from app.constants import DEFAULT_PLATFORM_SETTINGS_ID
from app.db.session import get_db
from app.models.platform import PlatformSettings

router = APIRouter(
    prefix="/v1/internal/platform",
    tags=["internal-platform"],
    dependencies=[Depends(require_internal_secret)],
)


class PlatformSettingsPatch(BaseModel):
    landing_whatsapp_e164: Optional[str] = Field(default=None, max_length=32)
    knowledge_base_text: Optional[str] = Field(default=None, max_length=200_000)


@router.get("/settings")
async def get_platform_settings(db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(PlatformSettings, DEFAULT_PLATFORM_SETTINGS_ID)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform settings not initialized")
    return {
        "id": str(row.id),
        "landing_whatsapp_e164": row.landing_whatsapp_e164,
        "knowledge_base_text": row.knowledge_base_text,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.patch("/settings")
async def patch_platform_settings(
    body: PlatformSettingsPatch,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == DEFAULT_PLATFORM_SETTINGS_ID))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform settings not initialized")

    if body.landing_whatsapp_e164 is not None:
        digits = "".join(c for c in body.landing_whatsapp_e164 if c.isdigit())
        row.landing_whatsapp_e164 = digits or None
    if body.knowledge_base_text is not None:
        row.knowledge_base_text = body.knowledge_base_text or None

    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "landing_whatsapp_e164": row.landing_whatsapp_e164,
        "knowledge_base_text": row.knowledge_base_text,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
