from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSetting

KEY_OUTPUT_GUARD = "agent_output_guard_enabled"
KEY_HUMANIZER = "agent_humanizer_enabled"

DEFAULT_OUTPUT_GUARD = True
DEFAULT_HUMANIZER = False


def get_bool_setting(db: Session, key: str, default: bool) -> bool:
    row = (
        db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        .scalars()
        .first()
    )
    if row is None or row.value is None:
        return default
    v = str(row.value).strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off", ""):
        return False
    return default


def is_output_guard_enabled(db: Session) -> bool:
    return get_bool_setting(db, KEY_OUTPUT_GUARD, DEFAULT_OUTPUT_GUARD)


def is_humanizer_enabled(db: Session) -> bool:
    return get_bool_setting(db, KEY_HUMANIZER, DEFAULT_HUMANIZER)


def set_bool_setting(db: Session, key: str, value: bool) -> None:
    row = (
        db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        .scalars()
        .first()
    )
    s = "true" if value else "false"
    if row is None:
        db.add(PlatformSetting(key=key, value=s))
    else:
        row.value = s
        db.add(row)
