"""Billing plans editable from the admin dashboard."""

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class BillingPlan(Base):
    __tablename__ = "billing_plans"

    # Stable key used across tenant rows (e.g. "lite", "standard", "premium")
    tier = mapped_column(String(32), primary_key=True)

    monthly_amount_ngn = mapped_column(Integer(), nullable=False)
    yearly_amount_ngn = mapped_column(Integer(), nullable=True)

    max_products = mapped_column(Integer(), nullable=False)
    max_users = mapped_column(Integer(), nullable=False)

    is_active = mapped_column(Boolean(), nullable=False, server_default="true")

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

