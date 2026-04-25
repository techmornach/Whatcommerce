"""platform_settings: flag for admin-requested whatcommerce session replacement

Revision ID: 20250424_0010
Revises: 20250424_0009
Create Date: 2026-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250424_0010"
down_revision: Union[str, None] = "20250424_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_settings",
        sa.Column(
            "whatcommerce_pending_session_reset",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_settings", "whatcommerce_pending_session_reset")
