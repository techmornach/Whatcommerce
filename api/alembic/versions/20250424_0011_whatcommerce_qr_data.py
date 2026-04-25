"""platform_settings: store latest whatcommerce pairing QR for admin UI

Revision ID: 20250424_0011
Revises: 20250424_0010
Create Date: 2026-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250424_0011"
down_revision: Union[str, None] = "20250424_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_settings",
        sa.Column("whatcommerce_qr_data", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_settings", "whatcommerce_qr_data")
