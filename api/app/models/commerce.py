import enum
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    pending_confirmation = "pending_confirmation"
    confirmed = "confirmed"
    rejected = "rejected"


class Product(Base):
    __tablename__ = "products"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(255), nullable=False)
    description = mapped_column(Text(), nullable=True)
    price_minor = mapped_column(Integer(), nullable=False, default=0)
    currency = mapped_column(String(8), nullable=False, default="NGN")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="products")


class Order(Base):
    __tablename__ = "orders"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_phone_e164 = mapped_column(String(32), nullable=False)
    customer_name = mapped_column(String(255), nullable=False)
    shipping_address = mapped_column(Text(), nullable=False)
    order_summary = mapped_column(Text(), nullable=True)
    status = mapped_column(String(32), nullable=False, default=OrderStatus.pending_confirmation.value)
    rejection_reason = mapped_column(Text(), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="orders")
