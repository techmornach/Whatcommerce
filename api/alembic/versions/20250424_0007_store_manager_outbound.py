"""store manager outbound queue for owner notifications

Revision ID: 20250424_0007
Revises: 20250424_0006
Create Date: 2025-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20250424_0007"
down_revision: Union[str, None] = "20250424_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_manager_outbound_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_phone_e164", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_sm_outbound_tenant", "store_manager_outbound_messages", ["tenant_id"], unique=False)
    op.create_index("ix_sm_outbound_status", "store_manager_outbound_messages", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sm_outbound_status", table_name="store_manager_outbound_messages")
    op.drop_index("ix_sm_outbound_tenant", table_name="store_manager_outbound_messages")
    op.drop_table("store_manager_outbound_messages")
