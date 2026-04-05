"""add api keys and tts provider

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('openai_api_key', sa.String(), nullable=True))
    op.add_column('companies', sa.Column('deepgram_api_key', sa.String(), nullable=True))
    op.add_column('companies', sa.Column('elevenlabs_api_key', sa.String(), nullable=True))
    op.add_column('companies', sa.Column('lemonslice_api_key', sa.String(), nullable=True))
    op.add_column('companies', sa.Column('tts_provider', sa.String(), nullable=True, server_default='openai'))


def downgrade() -> None:
    op.drop_column('companies', 'tts_provider')
    op.drop_column('companies', 'lemonslice_api_key')
    op.drop_column('companies', 'elevenlabs_api_key')
    op.drop_column('companies', 'deepgram_api_key')
    op.drop_column('companies', 'openai_api_key')
