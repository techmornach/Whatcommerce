from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "e6f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("cost_price_ngn", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("image_urls", sa.JSON(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("customer_name", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("customer_phone", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "customer_phone")
    op.drop_column("orders", "customer_name")
    op.drop_column("products", "image_urls")
    op.drop_column("products", "description")
    op.drop_column("products", "cost_price_ngn")
