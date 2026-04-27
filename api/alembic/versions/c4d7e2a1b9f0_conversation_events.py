"""conversation_events

Revision ID: c4d7e2a1b9f0
Revises: 8b2a3c0d1e2f
Create Date: 2026-04-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c4d7e2a1b9f0"
down_revision: str | None = "8b2a3c0d1e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("wa_chat_id", sa.String(length=128), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_events_phone_e164"),
        "conversation_events",
        ["phone_e164"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_events_tenant_id"),
        "conversation_events",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_events_user_id"),
        "conversation_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_events_wa_chat_id"),
        "conversation_events",
        ["wa_chat_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_events_phone_tenant",
        "conversation_events",
        ["phone_e164", "tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_events_phone_tenant", table_name="conversation_events")
    op.drop_index(op.f("ix_conversation_events_wa_chat_id"), table_name="conversation_events")
    op.drop_index(op.f("ix_conversation_events_user_id"), table_name="conversation_events")
    op.drop_index(op.f("ix_conversation_events_tenant_id"), table_name="conversation_events")
    op.drop_index(op.f("ix_conversation_events_phone_e164"), table_name="conversation_events")
    op.drop_table("conversation_events")
