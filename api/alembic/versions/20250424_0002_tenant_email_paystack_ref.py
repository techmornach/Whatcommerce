"""tenant owner email and paystack reference

Revision ID: 20250424_0002
Revises: 20250424_0001
Create Date: 2025-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250424_0002"
down_revision: Union[str, None] = "20250424_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("owner_email", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("last_paystack_reference", sa.String(length=128), nullable=True))
    op.create_index("ix_tenants_last_paystack_reference", "tenants", ["last_paystack_reference"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenants_last_paystack_reference", table_name="tenants")
    op.drop_column("tenants", "last_paystack_reference")
    op.drop_column("tenants", "owner_email")
