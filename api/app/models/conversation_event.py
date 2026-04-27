from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class ConversationEvent(TimestampMixin, Base):
    __tablename__ = "conversation_events"
    __table_args__ = (Index("ix_conversation_events_phone_tenant", "phone_e164", "tenant_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wa_chat_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "event_metadata", JSONB, nullable=True
    )

    tenant: Mapped[Tenant | None] = relationship("Tenant")
    user: Mapped[User | None] = relationship("User")
