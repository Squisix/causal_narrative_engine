"""Translate Spanish default values to English

Revision ID: 006_translate_defaults
Revises: 005_add_output_language
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = '006_translate_defaults'
down_revision: Union[str, None] = '005_add_output_language'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update column defaults
    op.alter_column('worlds', 'era', server_default='unknown')
    op.alter_column('worlds', 'rules', server_default='The world follows its own laws')
    op.alter_column('branches', 'name', server_default='Main branch')

    # Update existing data
    op.execute("UPDATE worlds SET era = 'unknown' WHERE era = 'desconocido'")
    op.execute("UPDATE worlds SET rules = 'The world follows its own laws' WHERE rules = 'El mundo sigue sus propias leyes'")
    op.execute("UPDATE branches SET name = 'Main branch' WHERE name = 'Rama principal'")


def downgrade() -> None:
    # Revert column defaults
    op.alter_column('worlds', 'era', server_default='desconocido')
    op.alter_column('worlds', 'rules', server_default='El mundo sigue sus propias leyes')
    op.alter_column('branches', 'name', server_default='Rama principal')

    # Revert existing data
    op.execute("UPDATE worlds SET era = 'desconocido' WHERE era = 'unknown'")
    op.execute("UPDATE worlds SET rules = 'El mundo sigue sus propias leyes' WHERE rules = 'The world follows its own laws'")
    op.execute("UPDATE branches SET name = 'Rama principal' WHERE name = 'Main branch'")
