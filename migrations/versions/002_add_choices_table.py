"""Add choices table

Revision ID: 002_add_choices_table
Revises: 001_initial_schema
Create Date: 2026-06-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002_add_choices_table'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'choices',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('commit_id', sa.String(36), nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('dramatic_preview', sa.JSON, server_default='{}'),
        sa.Column('tone_hint', sa.String(100), server_default=''),
        sa.Column('estimated_depth_until_ending', sa.Integer, nullable=True),
        sa.Column('display_order', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['commit_id'], ['commits.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_choices_commit', 'choices', ['commit_id'])


def downgrade() -> None:
    op.drop_index('idx_choices_commit', table_name='choices')
    op.drop_table('choices')
