"""initial

Revision ID: 9e210767dff5
Revises: 
Create Date: 2026-03-29 10:47:55.388191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9e210767dff5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('avatar_image_url', sa.String()),
        sa.Column('avatar_voice_id', sa.String()),
        sa.Column('avatar_prompt', sa.Text()),
        sa.Column('location_description', sa.String()),
        sa.Column('custom_rules', sa.Text()),
        sa.Column('allowed_topics', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('blocked_topics', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('enable_web_search', sa.Boolean(), server_default='false'),
        sa.Column('plan', sa.String(), server_default='starter'),
        sa.Column('minutes_limit', sa.Integer(), server_default='300'),
        sa.Column('minutes_used', sa.Float(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
    )
    op.create_index('ix_companies_slug', 'companies', ['slug'], unique=True)

    op.create_table(
        'knowledge_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_type', sa.String()),
        sa.Column('content_text', sa.Text()),
        sa.Column('chunks_count', sa.Integer(), server_default='0'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'dialogs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('duration_seconds', sa.Float()),
        sa.Column('language', sa.String(), server_default='ru'),
        sa.Column('satisfaction_score', sa.Integer()),
        sa.Column('topics', postgresql.JSON(astext_type=sa.Text())),
    )

    op.create_table(
        'dialog_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dialog_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dialogs.id'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('dialog_messages')
    op.drop_table('dialogs')
    op.drop_table('knowledge_documents')
    op.drop_index('ix_companies_slug', table_name='companies')
    op.drop_table('companies')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
