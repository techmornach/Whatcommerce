"""admin users + whatcommerce session metadata on platform_settings

Revision ID: 20250424_0009
Revises: 20250424_0008
Create Date: 2025-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20250424_0009"
down_revision: Union[str, None] = "20250424_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_by_id", UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)

    op.add_column(
        "platform_settings",
        sa.Column("whatcommerce_session_phone_e164", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "platform_settings",
        sa.Column("whatcommerce_session_ready_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_settings", "whatcommerce_session_ready_at")
    op.drop_column("platform_settings", "whatcommerce_session_phone_e164")
    op.drop_index("ix_admin_users_email", table_name="admin_users")
    op.drop_table("admin_users")
