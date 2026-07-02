"""Add entity_creations table for tracking runtime entity creation

Revision ID: 004_entity_creations
Revises: 003_add_causal_reason
Create Date: 2026-07-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '004_entity_creations'
down_revision: Union[str, None] = '003_add_causal_reason'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'entity_creations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('entity_name', sa.String(200), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('attributes', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('entity_creations')
