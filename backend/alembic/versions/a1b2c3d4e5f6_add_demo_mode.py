"""add demo mode

Revision ID: a1b2c3d4e5f6
Revises: 9e210767dff5
Create Date: 2026-04-02 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9e210767dff5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('demo_mode_enabled', sa.Boolean(), server_default='false'))

    op.create_table(
        'demo_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=False),
        sa.Column('seconds_used', sa.Float(), server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_demo_usage_company_ip', 'demo_usage', ['company_id', 'ip_address'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_demo_usage_company_ip', table_name='demo_usage')
    op.drop_table('demo_usage')
    op.drop_column('companies', 'demo_mode_enabled')
