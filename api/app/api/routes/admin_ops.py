import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, PlatformSetting
from app.services.bridge_status import BRIDGE_STATUS_KEY

router = APIRouter(prefix="/api/admin/ops", tags=["admin"])


class BridgeStatusOut(BaseModel):
    status: str = Field(
        default="unknown",
        description="ready | qr | error | unknown (never reported)",
    )
    message: str | None = None
    updated_at: str | None = None
    source: str = "bridge"


@router.get("/bridge-status", response_model=BridgeStatusOut)
def get_bridge_status(
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BridgeStatusOut:
    row = (
        db.execute(
            select(PlatformSetting).where(PlatformSetting.key == BRIDGE_STATUS_KEY)
        )
        .scalars()
        .first()
    )
    if not row or not (row.value or "").strip():
        return BridgeStatusOut()
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return BridgeStatusOut(
            status="error",
            message="Invalid bridge_status_json in platform_settings",
            source="config",
        )
    if not isinstance(data, dict):
        return BridgeStatusOut(status="error", message="Invalid payload shape", source="config")
    st = (str(data.get("status")) or "unknown") if data else "unknown"
    if st not in ("ready", "qr", "error", "unknown", "init"):
        st = "unknown"
    return BridgeStatusOut(
        status=str(st),
        message=data.get("message") if data.get("message") else None,
        updated_at=(str(data.get("updated_at")) if data.get("updated_at") else None),
    )
