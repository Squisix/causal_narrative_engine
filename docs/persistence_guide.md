# CNE Persistence Guide

CNE uses **SQLAlchemy 2.0 Async** alongside the **Repository Pattern** to map and save the narrative graph and snapshots into a PostgreSQL database.

---

## Technical Stack
- **Database Engine**: PostgreSQL 15+
- **ORM Framework**: SQLAlchemy 2.0 (Declarative Mapping style)
- **Async Driver**: `asyncpg`
- **Migrations Tool**: Alembic

---

## Persistence Schema

```
           +----------------------+
           |       WorldORM       |  (worlds table)
           +----------+-----------+
                      | 1:N
                      |
           +----------v-----------+
           |       EntityORM      |  (entities table)
           +----------------------+
                      |
                      | 1:N (dynamic creations)
           +----------v-----------+
           |  EntityCreationORM   |  (entity_creations table)
           +----------------------+
                      ^
                      | 1:N
           +----------+-----------+
           |       CommitORM      |  (commits table)
           +----------+-----------+
                      | 1:1
                      |
           +----------v-----------+
           |       EventORM       |  (events table)
           +----------------------+
```

### Table Definitions

1. **`worlds`**: Stems immutable seeds containing rules, era, protagonists, output language, and initial configurations.
2. **`entities`**: Keeps characters, factions, and artifacts. Instead of deletion, rows are flagged with `destroyed_at_depth` Narrative depth values.
3. **`events`**: Contains causal narrative prose, causal reasons, summaries, and associated world/entity deltas.
4. **`commits`**: Stores git-like history, parent relationships, choice labels, depth, and full-state snapshots (JSON schemas).

---

## Causal Queries with CTE

To enforce DAG properties and retrieve past history trees efficiently, CNE implements recursive Common Table Expressions (CTEs) at the SQL query level:

```sql
WITH RECURSIVE commit_history AS (
    SELECT id, parent_id, depth, summary
    FROM commits
    WHERE id = :target_commit_id
    
    UNION ALL
    
    SELECT c.id, c.parent_id, c.depth, c.summary
    FROM commits c
    JOIN commit_history h ON c.id = h.parent_id
)
SELECT * FROM commit_history;
```
This recursive query is implemented in `persistence/queries/causal_queries.py` to retrieve the active history trunk in a single fast, scalable SQL trip.
