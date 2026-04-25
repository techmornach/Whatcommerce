import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, relationship

from app.db.base import Base


class Customer(Base):
    """Customer record after first confirmed order (per planning)."""

    __tablename__ = "customers"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_e164 = mapped_column(String(32), nullable=False, index=True)
    display_name = mapped_column(String(255), nullable=True)
    notes = mapped_column(Text(), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="customers")
