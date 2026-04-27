from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import OnboardingState
from app.models.mixins import TimestampMixin


class OnboardingSession(TimestampMixin, Base):
    __tablename__ = "onboarding_sessions"
    __table_args__ = (UniqueConstraint("wa_chat_id", name="uq_onboarding_sessions_wa_chat_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wa_chat_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    state: Mapped[OnboardingState] = mapped_column(
        Enum(OnboardingState, name="onboarding_state", create_constraint=True, native_enum=False),
        default=OnboardingState.ask_name,
        index=True,
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tenant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
