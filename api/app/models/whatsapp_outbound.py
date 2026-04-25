"""Queued WhatsApp texts — platform (`whatcommerce`) or per-store (`store_manager`) worker."""

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class WhatsappOutboundMessage(Base):
    __tablename__ = "whatsapp_outbound_messages"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    to_phone_e164 = mapped_column(String(32), nullable=False)
    body = mapped_column(Text(), nullable=False)
    worker_channel = mapped_column(String(24), nullable=False, default="whatcommerce", index=True)
    status = mapped_column(String(16), nullable=False, default="pending", index=True)
    attempt_count = mapped_column(Integer(), nullable=False, default=0)
    last_error = mapped_column(Text(), nullable=True)
    failure_class = mapped_column(String(32), nullable=True)
    dead_letter_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
