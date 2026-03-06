"""Initial schema for CNE Fase 2

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-06

Crea todas las tablas del CNE con sus índices y constraints.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── WorldDefinition ────────────────────────────────────────────────────────
    op.create_table(
        'worlds',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('context', sa.Text, nullable=False),
        sa.Column('protagonist', sa.Text, nullable=False),
        sa.Column('era', sa.String(200), nullable=False),
        sa.Column('tone', sa.String(50), nullable=False),
        sa.Column('antagonist', sa.Text, default='desconocido'),
        sa.Column('rules', sa.Text, default='El mundo sigue sus propias leyes'),
        sa.Column('constraints', sa.JSON, default=list),
        sa.Column('dramatic_config', sa.JSON, nullable=False),
        sa.Column('max_depth', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── Entities ───────────────────────────────────────────────────────────────
    op.create_table(
        'entities',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('world_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('attributes', sa.JSON, default=dict),
        sa.Column('created_at_depth', sa.Integer, default=0),
        sa.Column('destroyed_at_depth', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_entities_world', 'entities', ['world_id'])
    op.create_index('idx_entities_alive', 'entities', ['destroyed_at_depth'], postgresql_where=sa.text('destroyed_at_depth IS NULL'))

    # ── Branches ───────────────────────────────────────────────────────────────
    op.create_table(
        'branches',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('world_id', sa.String(36), nullable=False),
        sa.Column('origin_commit_id', sa.String(36), nullable=False),
        sa.Column('leaf_commit_id', sa.String(36), nullable=True),
        sa.Column('name', sa.String(200), default='Rama principal'),
        sa.Column('description', sa.Text, default=''),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_branches_world', 'branches', ['world_id'])

    # ── Commits ────────────────────────────────────────────────────────────────
    op.create_table(
        'commits',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('world_id', sa.String(36), nullable=False),
        sa.Column('branch_id', sa.String(36), nullable=True),
        sa.Column('parent_id', sa.String(36), nullable=True),
        sa.Column('choice_text', sa.Text, nullable=True),
        sa.Column('narrative_text', sa.Text, nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('depth', sa.Integer, nullable=False),
        sa.Column('is_ending', sa.Boolean, default=False),
        sa.Column('world_state_snapshot', sa.JSON, default=dict),
        sa.Column('entity_states_snapshot', sa.JSON, default=dict),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_id'], ['commits.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_commits_world', 'commits', ['world_id'])
    op.create_index('idx_commits_parent', 'commits', ['parent_id'])
    op.create_index('idx_commits_depth', 'commits', ['depth'])
    op.create_index('idx_commits_branch', 'commits', ['branch_id'])

    # ── Events ─────────────────────────────────────────────────────────────────
    op.create_table(
        'events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('commit_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('narrative_text', sa.Text, nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('triggered_by_decision', sa.Text, nullable=True),
        sa.Column('forced_by_meter', sa.String(50), nullable=True),
        sa.Column('depth', sa.Integer, nullable=False),
        sa.Column('topo_order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['commit_id'], ['commits.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_events_commit', 'events', ['commit_id'])
    op.create_index('idx_events_depth', 'events', ['depth'])
    op.create_index('idx_events_topo', 'events', ['topo_order'])
    op.create_index('idx_events_forced', 'events', ['forced_by_meter'], postgresql_where=sa.text('forced_by_meter IS NOT NULL'))

    # ── Event Edges (DAG causal) ───────────────────────────────────────────────
    op.create_table(
        'event_edges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('cause_event_id', sa.String(36), nullable=False),
        sa.Column('effect_event_id', sa.String(36), nullable=False),
        sa.Column('relation_type', sa.String(50), default='direct'),
        sa.Column('strength', sa.Float, default=1.0),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['cause_event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['effect_event_id'], ['events.id'], ondelete='CASCADE'),
    )
    # ÍNDICES CRÍTICOS para queries causales (CTEs recursivas)
    op.create_index('idx_edges_cause', 'event_edges', ['cause_event_id'])
    op.create_index('idx_edges_effect', 'event_edges', ['effect_event_id'])
    op.create_index('idx_edges_both', 'event_edges', ['cause_event_id', 'effect_event_id'], unique=True)

    # ── Entity Deltas ──────────────────────────────────────────────────────────
    op.create_table(
        'entity_deltas',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('entity_name', sa.String(200), nullable=False),
        sa.Column('attribute', sa.String(100), nullable=False),
        sa.Column('old_value', sa.JSON, nullable=True),
        sa.Column('new_value', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_entity_deltas_event', 'entity_deltas', ['event_id'])
    op.create_index('idx_entity_deltas_entity', 'entity_deltas', ['entity_id'])

    # ── World Variable Deltas ──────────────────────────────────────────────────
    op.create_table(
        'world_variable_deltas',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), nullable=False),
        sa.Column('variable', sa.String(100), nullable=False),
        sa.Column('old_value', sa.JSON, nullable=True),
        sa.Column('new_value', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_world_deltas_event', 'world_variable_deltas', ['event_id'])

    # ── Dramatic States ────────────────────────────────────────────────────────
    op.create_table(
        'dramatic_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('commit_id', sa.String(36), nullable=False, unique=True),
        sa.Column('tension', sa.SmallInteger, nullable=False, default=30),
        sa.Column('hope', sa.SmallInteger, nullable=False, default=60),
        sa.Column('chaos', sa.SmallInteger, nullable=False, default=20),
        sa.Column('rhythm', sa.SmallInteger, nullable=False, default=50),
        sa.Column('saturation', sa.SmallInteger, nullable=False, default=0),
        sa.Column('connection', sa.SmallInteger, nullable=False, default=40),
        sa.Column('mystery', sa.SmallInteger, nullable=False, default=50),
        sa.Column('forced_event', sa.String(50), nullable=True),
        sa.Column('trigger_meter', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['commit_id'], ['commits.id'], ondelete='CASCADE'),
        # Constraints para validar rango [0-100]
        sa.CheckConstraint('tension >= 0 AND tension <= 100', name='check_tension_range'),
        sa.CheckConstraint('hope >= 0 AND hope <= 100', name='check_hope_range'),
        sa.CheckConstraint('chaos >= 0 AND chaos <= 100', name='check_chaos_range'),
        sa.CheckConstraint('rhythm >= 0 AND rhythm <= 100', name='check_rhythm_range'),
        sa.CheckConstraint('saturation >= 0 AND saturation <= 100', name='check_saturation_range'),
        sa.CheckConstraint('connection >= 0 AND connection <= 100', name='check_connection_range'),
        sa.CheckConstraint('mystery >= 0 AND mystery <= 100', name='check_mystery_range'),
    )
    op.create_index('idx_dramatic_commit', 'dramatic_states', ['commit_id'])
    op.create_index('idx_dramatic_forced', 'dramatic_states', ['forced_event'], postgresql_where=sa.text('forced_event IS NOT NULL'))

    # ── Dramatic Deltas (para el paper) ────────────────────────────────────────
    op.create_table(
        'dramatic_deltas',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), nullable=False),
        sa.Column('meter', sa.String(50), nullable=False),
        sa.Column('delta', sa.SmallInteger, nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_dramatic_deltas_event', 'dramatic_deltas', ['event_id'])
    op.create_index('idx_dramatic_deltas_meter', 'dramatic_deltas', ['meter'])


def downgrade() -> None:
    # Borrar en orden inverso (respetando foreign keys)
    op.drop_table('dramatic_deltas')
    op.drop_table('dramatic_states')
    op.drop_table('world_variable_deltas')
    op.drop_table('entity_deltas')
    op.drop_table('event_edges')
    op.drop_table('events')
    op.drop_table('commits')
    op.drop_table('branches')
    op.drop_table('entities')
    op.drop_table('worlds')
