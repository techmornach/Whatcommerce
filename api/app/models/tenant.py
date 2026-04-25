import enum
import uuid

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, relationship

from app.db.base import Base


class PlanTier(str, enum.Enum):
    lite = "lite"
    standard = "standard"
    premium = "premium"


class TenantStatus(str, enum.Enum):
    inactive = "inactive"
    active = "active"


class Tenant(Base):
    __tablename__ = "tenants"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_name = mapped_column(String(255), nullable=False)
    business_name = mapped_column(String(255), nullable=False)
    business_address = mapped_column(Text(), nullable=False)
    plan_tier = mapped_column(String(32), nullable=False, default=PlanTier.lite.value)
    billing_period = mapped_column(String(16), nullable=False, default="monthly")
    status = mapped_column(String(32), nullable=False, default=TenantStatus.inactive.value)
    plan_expires_at = mapped_column(DateTime(timezone=True), nullable=True)
    onboarding_phone_e164 = mapped_column(String(32), nullable=False, index=True)
    owner_email = mapped_column(String(255), nullable=True)
    last_paystack_reference = mapped_column(String(128), nullable=True, index=True)
    wa_link_token = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    wa_link_expires_at = mapped_column(DateTime(timezone=True), nullable=True)
    store_manager_phone_e164 = mapped_column(String(32), nullable=True, index=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    products = relationship("Product", back_populates="tenant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="tenant", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="tenant", cascade="all, delete-orphan")
