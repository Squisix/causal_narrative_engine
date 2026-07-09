"""Drop dramatic_preview column from choices table

Revision ID: 007_drop_dramatic_preview
Revises: 006_translate_defaults
Create Date: 2026-07-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '007_drop_dramatic_preview'
down_revision: Union[str, None] = '006_translate_defaults'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('choices', 'dramatic_preview')


def downgrade() -> None:
    op.add_column('choices', sa.Column('dramatic_preview', sa.JSON, server_default='{}'))
