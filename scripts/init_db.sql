-- scripts/init_db.sql
-- Script de inicialización de PostgreSQL
-- Se ejecuta automáticamente cuando se crea el contenedor

-- Crear extensión para UUID (aunque asyncpg ya lo soporta nativamente)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Configuración para mejor performance con JSON
ALTER DATABASE cne_db SET timezone TO 'UTC';

-- Índices que se crearán por Alembic, pero los documentamos aquí

-- Tabla: events
--   INDEX idx_events_commit_id ON events(commit_id)
--   INDEX idx_events_depth ON events(depth)
--   INDEX idx_events_topo_order ON events(topo_order)

-- Tabla: event_edges (CRÍTICO para queries causales)
--   INDEX idx_edges_cause ON event_edges(cause_event_id)
--   INDEX idx_edges_effect ON event_edges(effect_event_id)
--   INDEX idx_edges_both ON event_edges(cause_event_id, effect_event_id)

-- Tabla: commits
--   INDEX idx_commits_world_id ON commits(world_id)
--   INDEX idx_commits_parent_id ON commits(parent_id)
--   INDEX idx_commits_depth ON commits(depth)
--   INDEX idx_commits_branch_id ON commits(branch_id)

-- Tabla: dramatic_states
--   INDEX idx_dramatic_commit ON dramatic_states(commit_id)
--   INDEX idx_dramatic_tension ON dramatic_states(tension)
--   INDEX idx_dramatic_forced ON dramatic_states(forced_event) WHERE forced_event IS NOT NULL

-- Nota: Las tablas las crea Alembic, no este script
-- Este archivo es solo para extensiones y configuración inicial
