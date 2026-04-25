from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class OnboardingSession(Base):
    """Deterministic signup flow for the Whatcommerce WhatsApp bot (per phone)."""

    __tablename__ = "onboarding_sessions"

    phone_e164 = mapped_column(String(32), primary_key=True)
    state = mapped_column(String(64), nullable=False)
    data = mapped_column(JSONB, nullable=False)
    tenant_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
