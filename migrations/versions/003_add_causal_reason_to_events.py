"""Add causal_reason column to events table

Revision ID: 003_add_causal_reason
Revises: 002_add_choices_table
Create Date: 2026-07-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003_add_causal_reason'
down_revision: Union[str, None] = '002_add_choices_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('causal_reason', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column('events', 'causal_reason')
