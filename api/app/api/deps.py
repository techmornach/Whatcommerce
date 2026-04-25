from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
import jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_admin_token, parse_uuid_sub
from app.db.session import get_db
from app.models.admin_user import AdminRole, AdminUser

_admin_bearer = HTTPBearer(auto_error=False)


def require_internal_secret(
    x_internal_secret: Optional[str] = Header(default=None, alias="X-Internal-Secret"),
) -> None:
    expected = get_settings().internal_api_secret
    if not x_internal_secret or x_internal_secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing internal secret")


async def get_current_admin(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_admin_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUser:
    if creds is None or (creds.scheme or "").lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_admin_token(creds.credentials)
        admin_id: UUID = parse_uuid_sub(payload)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = await db.get(AdminUser, admin_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


def require_super_admin(admin: Annotated[AdminUser, Depends(get_current_admin)]) -> AdminUser:
    if admin.role != AdminRole.super_admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin required")
    return admin
