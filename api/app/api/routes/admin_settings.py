from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, PlatformSetting
from app.services.bridge_status import parse_public_bridge_state
from app.services.guard_reporting import KEY_GUARD_REPORT_E164
from app.services.platform_agent_flags import (
    DEFAULT_HUMANIZER,
    DEFAULT_OUTPUT_GUARD,
    KEY_HUMANIZER,
    KEY_OUTPUT_GUARD,
    get_bool_setting,
    set_bool_setting,
)

router = APIRouter(prefix="/api/admin/settings", tags=["admin"])


class WhatsAppLandingOut(BaseModel):
    link_state: str
    connected_whatsapp_e164: str | None
    bridge_status: str | None
    bridge_message: str | None
    bridge_updated_at: str | None
    qr_data: str | None
    landing_message_prefill: str


class WhatsAppPrefillIn(BaseModel):
    landing_message_prefill: str = Field(default="", max_length=2000)


class AgentPipelineOut(BaseModel):
    agent_output_guard_enabled: bool
    agent_humanizer_enabled: bool
    guard_report_whatsapp_e164: str = ""


class AgentPipelineIn(BaseModel):
    agent_output_guard_enabled: bool | None = None
    agent_humanizer_enabled: bool | None = None
    guard_report_whatsapp_e164: str | None = None


def _set(db: Session, key: str, value: str) -> None:
    row = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalars().first()
    if row is None:
        db.add(PlatformSetting(key=key, value=value))
    else:
        row.value = value
        db.add(row)


def _compute_link_state(st: str | None, phone: str | None) -> str:
    if st == "ready" and (phone or "").strip():
        return "linked"
    if st in ("qr", "init"):
        return "pairing"
    return "unlinked"


def _whatsapp_landing_out(db: Session) -> WhatsAppLandingOut:
    parsed = parse_public_bridge_state(db)
    st = parsed.get("status")
    phone = (parsed.get("connected_e164") or "").strip() or None
    pre = (
        db.execute(
            select(PlatformSetting).where(PlatformSetting.key == "landing_message_prefill")
        )
        .scalars()
        .first()
    )
    prefill = pre.value if pre and pre.value else ""
    return WhatsAppLandingOut(
        link_state=_compute_link_state(st, phone),
        connected_whatsapp_e164=phone,
        bridge_status=st,
        bridge_message=parsed.get("message"),
        bridge_updated_at=parsed.get("updated_at"),
        qr_data=parsed.get("qr_data"),
        landing_message_prefill=prefill,
    )


@router.get("/whatsapp", response_model=WhatsAppLandingOut)
def get_whatsapp_landing(
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> WhatsAppLandingOut:
    return _whatsapp_landing_out(db)


@router.put("/whatsapp", response_model=WhatsAppLandingOut)
def put_whatsapp_prefill(
    body: WhatsAppPrefillIn,
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> WhatsAppLandingOut:
    _set(db, "landing_message_prefill", body.landing_message_prefill)
    db.commit()
    return _whatsapp_landing_out(db)


def _agent_pipeline_out(db: Session) -> AgentPipelineOut:
    rep = (
        db.execute(
            select(PlatformSetting).where(PlatformSetting.key == KEY_GUARD_REPORT_E164)
        )
        .scalars()
        .first()
    )
    rep_s = (rep.value or "").strip() if rep else ""
    return AgentPipelineOut(
        agent_output_guard_enabled=get_bool_setting(
            db, KEY_OUTPUT_GUARD, DEFAULT_OUTPUT_GUARD
        ),
        agent_humanizer_enabled=get_bool_setting(
            db, KEY_HUMANIZER, DEFAULT_HUMANIZER
        ),
        guard_report_whatsapp_e164=rep_s,
    )


@router.get("/agent-pipeline", response_model=AgentPipelineOut)
def get_agent_pipeline(
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AgentPipelineOut:
    return _agent_pipeline_out(db)


@router.put("/agent-pipeline", response_model=AgentPipelineOut)
def put_agent_pipeline(
    body: AgentPipelineIn,
    _: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AgentPipelineOut:
    if body.agent_output_guard_enabled is not None:
        set_bool_setting(db, KEY_OUTPUT_GUARD, body.agent_output_guard_enabled)
    if body.agent_humanizer_enabled is not None:
        set_bool_setting(db, KEY_HUMANIZER, body.agent_humanizer_enabled)
    if body.guard_report_whatsapp_e164 is not None:
        _set(db, KEY_GUARD_REPORT_E164, body.guard_report_whatsapp_e164.strip())
    db.commit()
    return _agent_pipeline_out(db)
