"""order line summary text

Revision ID: 20250424_0006
Revises: 20250424_0005
Create Date: 2025-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250424_0006"
down_revision: Union[str, None] = "20250424_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("order_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "order_summary")
