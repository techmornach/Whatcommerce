import uuid

from sqlalchemy import Boolean, DateTime, String, Text, false, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class PlatformSettings(Base):
    """Singleton-style row for super-admin–controlled public config."""

    __tablename__ = "platform_settings"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    landing_whatsapp_e164 = mapped_column(String(32), nullable=True)
    knowledge_base_text = mapped_column(Text(), nullable=True)
    # Last successful whatcommerce *platform* worker (whatsapp-web.js) session — not store-manager tenants
    whatcommerce_session_phone_e164 = mapped_column(String(32), nullable=True)
    whatcommerce_session_ready_at = mapped_column(DateTime(timezone=True), nullable=True)
    # Worker polls; when true it destroys LocalAuth, clears this flag, and shows QR again.
    whatcommerce_pending_session_reset = mapped_column(
        Boolean(), nullable=False, server_default=false()
    )
    # whatsapp-web.js `qr` event payload — shown in admin until session-ready clears it
    whatcommerce_qr_data = mapped_column(Text(), nullable=True)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
