import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure 'app' is importable when running alembic from api/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from app.core.config import get_settings
from app.db.base import Base
from app.models import (  # noqa: F401
    AdminUser,
    BillingPlan,
    ConversationEvent,
    KnowledgeChunk,
    KnowledgeDocument,
    OnboardingSession,
    Order,
    OrderLine,
    PaystackProcessedReference,
    PlatformSetting,
    Product,
    Tenant,
    User,
)

# Import metadata from models
_ = (
    AdminUser,
    BillingPlan,
    ConversationEvent,
    KnowledgeChunk,
    KnowledgeDocument,
    OnboardingSession,
    Order,
    OrderLine,
    PaystackProcessedReference,
    PlatformSetting,
    Product,
    Tenant,
    User,
)
target_metadata = Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = (config.get_section(config.config_ini_section) or {}).copy()
    section["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
