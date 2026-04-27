from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TenantStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.billing_plan import BillingPlan
    from app.models.product import Product
    from app.models.user import User


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_name: Mapped[str] = mapped_column(String(256))
    business_address: Mapped[str] = mapped_column(Text)
    contact_email: Mapped[str] = mapped_column(String(512), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("billing_plans.id"), index=True)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status", create_constraint=True, native_enum=False),
        default=TenantStatus.inactive,
        index=True,
    )
    subscription_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paystack_last_reference: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )

    plan: Mapped["BillingPlan"] = relationship("BillingPlan", back_populates="tenants")
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="tenant", cascade="all, delete-orphan"
    )
