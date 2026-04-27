import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSetting
from app.utils.phone import normalize_to_e164

BRIDGE_STATUS_KEY = "bridge_status_json"
CONNECTED_WHATSAPP_E164_KEY = "connected_whatsapp_e164"
BRIDGE_QR_DATA_KEY = "bridge_qr_data"


def _get_setting_value(db: Session, key: str) -> str | None:
    row = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalars().first()
    if row is None or row.value is None:
        return None
    return str(row.value)


def _set_setting(db: Session, key: str, value: str) -> None:
    row = (
        db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        .scalars()
        .first()
    )
    if row is None:
        db.add(PlatformSetting(key=key, value=value))
    else:
        row.value = value
        db.add(row)


def _write_bridge_status_json(db: Session, status: str, message: str | None) -> None:
    now = datetime.now(UTC).isoformat()
    payload = json.dumps(
        {"status": status, "message": message, "updated_at": now},
        ensure_ascii=False,
    )
    _set_setting(db, BRIDGE_STATUS_KEY, payload)


def apply_bridge_report(
    db: Session,
    *,
    status: str,
    message: str | None = None,
    qr_data: str | None = None,
    phone_e164: str | None = None,
) -> None:
    """
    Single transaction: bridge heartbeat + optional QR (pairing) + optional phone (ready).
    Heartbeat-only posts omit phone_e164 so we do not clear the stored number.
    """
    st = (status or "error").lower().strip()
    if st not in ("ready", "qr", "error", "init"):
        st = "error"

    _write_bridge_status_json(db, st, message)

    if st == "qr":
        if qr_data and (q := (qr_data or "").strip()):
            _set_setting(db, BRIDGE_QR_DATA_KEY, q[:20_000])
        _set_setting(db, CONNECTED_WHATSAPP_E164_KEY, "")

    elif st in ("init",):
        if qr_data and (q := (qr_data or "").strip()):
            _set_setting(db, BRIDGE_QR_DATA_KEY, q[:20_000])

    elif st == "ready":
        _set_setting(db, BRIDGE_QR_DATA_KEY, "")
        if (phone_e164 or "").strip():
            n = normalize_to_e164(phone_e164.strip())
            if n:
                _set_setting(db, CONNECTED_WHATSAPP_E164_KEY, n)

    elif st == "error":
        _set_setting(db, BRIDGE_QR_DATA_KEY, "")
        _set_setting(db, CONNECTED_WHATSAPP_E164_KEY, "")

    db.commit()


def save_bridge_status(db: Session, status: str, message: str | None = None) -> None:
    """Backward-compatible: status + message only (used when no extra payload)."""
    apply_bridge_report(db, status=status, message=message)


def parse_public_bridge_state(db: Session) -> dict[str, str | None]:
    """Return {status, message, updated_at, connected_e164, qr_data}."""
    raw = _get_setting_value(db, BRIDGE_STATUS_KEY)
    out: dict[str, str | None] = {
        "status": None,
        "message": None,
        "updated_at": None,
    }
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                s0 = data.get("status")
                out["status"] = str(s0) if s0 is not None else None
                m0 = data.get("message")
                out["message"] = str(m0) if m0 is not None else None
                u0 = data.get("updated_at")
                out["updated_at"] = str(u0) if u0 is not None else None
        except (json.JSONDecodeError, TypeError):
            pass
    out["connected_e164"] = _get_setting_value(db, CONNECTED_WHATSAPP_E164_KEY)
    out["qr_data"] = _get_setting_value(db, BRIDGE_QR_DATA_KEY)
    return out
