from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '15e03674ff1e'
down_revision: Union[str, None] = '5d1d9cd80e8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('paystack_processed_references',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('reference', sa.String(length=128), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=True),
    sa.Column('event_type', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_paystack_processed_references_reference'), 'paystack_processed_references', ['reference'], unique=True)
    op.create_index(op.f('ix_paystack_processed_references_tenant_id'), 'paystack_processed_references', ['tenant_id'], unique=False)
    op.add_column('tenants', sa.Column('paystack_last_reference', sa.String(length=128), nullable=True))
    op.create_index(op.f('ix_tenants_paystack_last_reference'), 'tenants', ['paystack_last_reference'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tenants_paystack_last_reference'), table_name='tenants')
    op.drop_column('tenants', 'paystack_last_reference')
    op.drop_index(op.f('ix_paystack_processed_references_tenant_id'), table_name='paystack_processed_references')
    op.drop_index(op.f('ix_paystack_processed_references_reference'), table_name='paystack_processed_references')
    op.drop_table('paystack_processed_references')
