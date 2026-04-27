import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models import AdminUser, BillingPlan, PlatformSetting

logger = logging.getLogger(__name__)

PLANS: list[dict] = [
    {
        "key": "lite",
        "name": "Lite",
        "max_products": 50,
        "price_monthly_ngn": 5_000,
        "price_yearly_ngn": 50_000,
        "display_order": 0,
    },
    {
        "key": "standard",
        "name": "Standard",
        "max_products": 100,
        "price_monthly_ngn": 10_000,
        "price_yearly_ngn": 100_000,
        "display_order": 1,
    },
    {
        "key": "premium",
        "name": "Premium",
        "max_products": 500,
        "price_monthly_ngn": 20_000,
        "price_yearly_ngn": 200_000,
        "display_order": 2,
    },
]

DEFAULT_SETTINGS: dict[str, str] = {
    "landing_whatsapp_e164": "+2348000000000",
    "landing_message_prefill": "Hi! I'd like to get started with Whatcommerce.",
    "agent_output_guard_enabled": "true",
    "agent_humanizer_enabled": "false",
    "guard_report_whatsapp_e164": "",
}


def seed_billing_plans(db: Session) -> None:
    for row in PLANS:
        existing = (
            db.execute(select(BillingPlan).where(BillingPlan.key == row["key"])).scalars().first()
        )
        if existing is not None:
            continue
        db.add(
            BillingPlan(
                key=row["key"],
                name=row["name"],
                max_products=row["max_products"],
                price_monthly_ngn=row["price_monthly_ngn"],
                price_yearly_ngn=row["price_yearly_ngn"],
                display_order=row["display_order"],
                is_active=True,
            )
        )
    db.commit()
    logger.info("Billing plans ensured")


def seed_platform_settings(db: Session) -> None:
    for k, v in DEFAULT_SETTINGS.items():
        existing = (
            db.execute(select(PlatformSetting).where(PlatformSetting.key == k))
            .scalars()
            .first()
        )
        if existing is not None:
            continue
        db.add(PlatformSetting(key=k, value=v))
    db.commit()
    logger.info("Platform settings ensured")


def create_bootstrap_admin_if_configured(db: Session) -> None:
    settings = get_settings()
    if (
        not settings.bootstrap_admin
        or not settings.admin_bootstrap_email
        or not settings.admin_bootstrap_password
    ):
        return
    email = settings.admin_bootstrap_email.strip().lower()
    if db.execute(select(AdminUser).where(AdminUser.email == email)).scalars().first() is not None:
        return
    db.add(
        AdminUser(
            email=email,
            password_hash=get_password_hash(settings.admin_bootstrap_password),
        )
    )
    db.commit()
    logger.info("Created bootstrap super admin: %s", email)


def run_startup_bootstrap() -> None:
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        try:
            seed_billing_plans(db)
        except Exception:
            db.rollback()
            raise
    with SessionLocal() as db:
        try:
            seed_platform_settings(db)
        except Exception:
            db.rollback()
            raise
    with SessionLocal() as db:
        try:
            create_bootstrap_admin_if_configured(db)
        except Exception:
            db.rollback()
            raise
    logger.info("Startup bootstrap completed at %s", datetime.now(UTC).isoformat())
