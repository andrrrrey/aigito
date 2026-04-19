"""add avatar_memory_enabled

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-04-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('avatar_memory_enabled', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('companies', 'avatar_memory_enabled')
