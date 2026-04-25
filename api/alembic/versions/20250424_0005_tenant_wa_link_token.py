"""tenant whatsapp store-link token for post-payment QR page

Revision ID: 20250424_0005
Revises: 20250424_0004
Create Date: 2025-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20250424_0005"
down_revision: Union[str, None] = "20250424_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("wa_link_token", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tenants", sa.Column("wa_link_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tenants_wa_link_token", "tenants", ["wa_link_token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenants_wa_link_token", table_name="tenants")
    op.drop_column("tenants", "wa_link_expires_at")
    op.drop_column("tenants", "wa_link_token")
