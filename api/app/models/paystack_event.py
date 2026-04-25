from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class PaystackProcessedReference(Base):
    """One row per Paystack `reference` we have successfully applied (idempotent webhooks)."""

    __tablename__ = "paystack_processed_references"

    reference = mapped_column(String(128), primary_key=True)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
