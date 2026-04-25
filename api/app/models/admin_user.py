"""Dashboard admins (platform / Whatcommerce ops — not tenant store managers)."""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class AdminRole(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash = mapped_column(String(255), nullable=False)
    role = mapped_column(String(32), nullable=False, default=AdminRole.admin.value)
    is_active = mapped_column(Boolean(), nullable=False, default=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
