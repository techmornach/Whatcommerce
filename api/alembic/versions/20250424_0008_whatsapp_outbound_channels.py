"""whatsapp outbound: rename table, worker channel, attempts, dead-letter

Revision ID: 20250424_0008
Revises: 20250424_0007
Create Date: 2025-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250424_0008"
down_revision: Union[str, None] = "20250424_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("store_manager_outbound_messages", "whatsapp_outbound_messages")
    op.drop_index("ix_sm_outbound_status", table_name="whatsapp_outbound_messages")
    op.drop_index("ix_sm_outbound_tenant", table_name="whatsapp_outbound_messages")

    op.add_column(
        "whatsapp_outbound_messages",
        sa.Column("worker_channel", sa.String(length=24), nullable=True),
    )
    op.execute(
        "UPDATE whatsapp_outbound_messages SET worker_channel = 'store_manager' WHERE worker_channel IS NULL"
    )
    op.alter_column(
        "whatsapp_outbound_messages",
        "worker_channel",
        existing_type=sa.String(length=24),
        nullable=False,
        server_default=sa.text("'whatcommerce'::character varying(24)"),
    )

    op.add_column(
        "whatsapp_outbound_messages",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("whatsapp_outbound_messages", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("whatsapp_outbound_messages", sa.Column("failure_class", sa.String(length=32), nullable=True))
    op.add_column(
        "whatsapp_outbound_messages",
        sa.Column("dead_letter_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_wa_outbound_tenant", "whatsapp_outbound_messages", ["tenant_id"], unique=False)
    op.create_index("ix_wa_outbound_status", "whatsapp_outbound_messages", ["status"], unique=False)
    op.create_index("ix_wa_outbound_channel", "whatsapp_outbound_messages", ["worker_channel"], unique=False)
    op.create_index("ix_wa_outbound_dead_letter", "whatsapp_outbound_messages", ["dead_letter_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wa_outbound_dead_letter", table_name="whatsapp_outbound_messages")
    op.drop_index("ix_wa_outbound_channel", table_name="whatsapp_outbound_messages")
    op.drop_index("ix_wa_outbound_status", table_name="whatsapp_outbound_messages")
    op.drop_index("ix_wa_outbound_tenant", table_name="whatsapp_outbound_messages")
    op.drop_column("whatsapp_outbound_messages", "dead_letter_at")
    op.drop_column("whatsapp_outbound_messages", "failure_class")
    op.drop_column("whatsapp_outbound_messages", "last_error")
    op.drop_column("whatsapp_outbound_messages", "attempt_count")
    op.drop_column("whatsapp_outbound_messages", "worker_channel")
    op.rename_table("whatsapp_outbound_messages", "store_manager_outbound_messages")
    op.create_index("ix_sm_outbound_tenant", "store_manager_outbound_messages", ["tenant_id"], unique=False)
    op.create_index("ix_sm_outbound_status", "store_manager_outbound_messages", ["status"], unique=False)
