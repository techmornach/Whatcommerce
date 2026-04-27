from enum import StrEnum


class TenantStatus(StrEnum):
    inactive = "inactive"
    active = "active"
    suspended = "suspended"


class UserRole(StrEnum):
    owner = "owner"
    staff = "staff"


class OrderStatus(StrEnum):
    pending = "pending"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class OnboardingState(StrEnum):
    ask_name = "ask_name"
    ask_business = "ask_business"
    ask_address = "ask_address"
    ask_email = "ask_email"
    ask_plan = "ask_plan"
    ask_billing = "ask_billing"
    payment_sent = "payment_sent"
    complete = "complete"
