"""Password hashing and JWT for dashboard admins."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings

_BCRYPT_MAX_BYTES = 72


def _password_bytes(raw: str) -> bytes:
    """bcrypt only accepts the first 72 UTF-8 bytes."""
    return raw.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(raw: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    digest = bcrypt.hashpw(_password_bytes(raw), salt)
    return digest.decode("ascii")


def verify_password(raw: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(raw), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_admin_access_token(*, admin_id: UUID, email: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.admin_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(admin_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.admin_jwt_secret,
        algorithm=settings.admin_jwt_algorithm,
    )
    return token if isinstance(token, str) else token.decode("utf-8")


def decode_admin_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.admin_jwt_secret,
        algorithms=[settings.admin_jwt_algorithm],
    )


def parse_uuid_sub(payload: dict[str, Any]) -> UUID:
    sub = payload.get("sub")
    if not sub:
        raise ValueError("missing sub")
    return UUID(str(sub))
