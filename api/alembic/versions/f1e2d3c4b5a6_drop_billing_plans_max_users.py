"""drop max_users from billing_plans

Revision ID: f1e2d3c4b5a6
Revises: 8b2a3c0d1e2f
Create Date: 2026-04-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1e2d3c4b5a6"
down_revision: str | None = "8b2a3c0d1e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("billing_plans", "max_users")


def downgrade() -> None:
    op.add_column(
        "billing_plans",
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("billing_plans", "max_users", server_default=None)
