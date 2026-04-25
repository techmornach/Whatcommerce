"""paystack processed reference idempotency

Revision ID: 20250424_0003
Revises: 20250424_0002
Create Date: 2025-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20250424_0003"
down_revision: Union[str, None] = "20250424_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paystack_processed_references",
        sa.Column("reference", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("reference"),
    )


def downgrade() -> None:
    op.drop_table("paystack_processed_references")
