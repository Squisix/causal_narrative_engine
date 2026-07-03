"""Add output_language column to worlds table

Revision ID: 005_add_output_language
Revises: 004_entity_creations
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005_add_output_language'
down_revision: Union[str, None] = '004_entity_creations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add output_language column to worlds table with default 'es'
    op.add_column(
        'worlds',
        sa.Column('output_language', sa.String(10), nullable=False, server_default='es')
    )


def downgrade() -> None:
    # Remove output_language column from worlds table
    op.drop_column('worlds', 'output_language')
