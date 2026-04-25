"""billing_plans: DB-backed plan config editable in admin

Revision ID: 20250425_0001
Revises: 20250424_0011
Create Date: 2026-04-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250425_0001"
down_revision: Union[str, None] = "20250424_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_plans",
        sa.Column("tier", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("monthly_amount_ngn", sa.Integer(), nullable=False),
        sa.Column("yearly_amount_ngn", sa.Integer(), nullable=True),
        sa.Column("max_products", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_billing_plans_active", "billing_plans", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_plans_active", table_name="billing_plans")
    op.drop_table("billing_plans")

