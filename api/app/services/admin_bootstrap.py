"""Optional first super_admin from environment (dev / first deploy)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.admin_user import AdminRole, AdminUser

logger = logging.getLogger(__name__)


def _norm_email(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().lower()
    return s if s else None


async def ensure_bootstrap_admin(db: AsyncSession) -> None:
    settings = get_settings()
    email = _norm_email(settings.bootstrap_admin_email)
    password = settings.bootstrap_admin_password
    if not email or not password:
        return

    cnt = await db.scalar(select(func.count()).select_from(AdminUser))
    if int(cnt or 0) > 0:
        return

    db.add(
        AdminUser(
            email=email,
            password_hash=hash_password(password),
            role=AdminRole.super_admin.value,
            is_active=True,
            created_by_id=None,
        )
    )
    await db.commit()
    logger.warning("Created bootstrap super_admin %s (set BOOTSTRAP_ADMIN_* off in production)", email)
