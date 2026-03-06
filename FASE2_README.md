# Fase 2 — Persistencia con PostgreSQL

## ¿Qué se agregó en Fase 2?

- ✅ **Repository Pattern**: interfaz abstracta `NarrativeRepository`
- ✅ **ORM Models**: SQLAlchemy 2.0 async para todas las tablas
- ✅ **Implementación PostgreSQL**: `PostgreSQLRepository`
- ✅ **Queries causales**: CTE recursiva para detectar ciclos en el DAG
- ✅ **StateRebuilder**: reconstrucción de estado desde deltas (estructura base)
- ✅ **Migraciones**: Alembic con schema inicial completo
- ✅ **Docker Compose**: PostgreSQL + Adminer + Redis
- ✅ **Tests**: Suite completa de tests async

---

## Instalación

### 1. Instalar dependencias

```bash
# Desde el directorio raíz del proyecto
pip install -e ".[persistence,dev]"
```

Esto instala:
- `sqlalchemy[asyncio]>=2.0.0`
- `alembic>=1.13.0`
- `asyncpg>=0.29.0` (driver async para PostgreSQL)
- `pytest-asyncio>=0.23.0` (para tests async)

### 2. Levantar PostgreSQL con Docker

```bash
# Levantar servicios (PostgreSQL + Adminer + Redis)
docker-compose up -d

# Ver logs
docker-compose logs -f postgres

# Verificar que PostgreSQL esté corriendo
docker ps
```

**Servicios disponibles:**
- PostgreSQL: `localhost:5432`
- Adminer (UI web): `http://localhost:8080`
- Redis: `localhost:6379` (para Fase 4+)

**Conexión string:**
```
postgresql+asyncpg://cne_user:cne_password_dev@localhost:5432/cne_db
```

### 3. Aplicar migraciones

```bash
# Crear las tablas en PostgreSQL
alembic upgrade head

# Ver estado de migraciones
alembic current

# Ver historial
alembic history
```

---

## Ejecutar tests

```bash
# Todos los tests de Fase 2
pytest tests/test_fase2.py -v

# Solo tests marcados con @pytest.mark.fase2
pytest -m fase2 -v

# Con coverage
pytest tests/test_fase2.py --cov=persistence --cov-report=term-missing
```

**Requisitos para los tests:**
- Docker corriendo con `docker-compose up -d`
- Migraciones aplicadas: `alembic upgrade head`

---

## Estructura de Fase 2

```
cne_core/
├── interfaces/                      # ✨ NUEVO
│   ├── repository.py                # Interfaz abstracta NarrativeRepository
│   └── ai_adapter.py                # Interfaz abstracta AIAdapter (Fase 3)
│
persistence/                         # ✨ NUEVO
├── database.py                      # Config de SQLAlchemy 2.0 async
├── models/                          # ORM models
│   ├── world_orm.py                 # WorldORM, EntityORM
│   ├── event_orm.py                 # EventORM, CausalEdgeORM, deltas
│   └── commit_orm.py                # CommitORM, DramaticStateORM
├── repositories/
│   └── postgresql_repository.py    # Implementación concreta
├── queries/
│   └── causal_queries.py            # CTEs recursivas
└── state_rebuilder.py               # Reconstrucción de estado

migrations/                          # ✨ NUEVO
├── env.py                           # Config de Alembic async
├── script.py.mako                   # Template para migraciones
└── versions/
    └── 001_initial_schema.py        # Migración inicial

tests/
└── test_fase2.py                    # ✨ NUEVO

docker-compose.yml                   # ✨ NUEVO
alembic.ini                          # ✨ NUEVO
pyproject.toml                       # Actualizado con deps de Fase 2
```

---

## Tablas creadas

| Tabla | Descripción | Índices críticos |
|-------|-------------|------------------|
| `worlds` | WorldDefinition (semilla) | — |
| `entities` | Personajes, objetos, lugares | `idx_entities_alive` |
| `branches` | Metadata de ramas | `idx_branches_world` |
| `commits` | Árbol de decisiones | `idx_commits_parent`, `idx_commits_depth` |
| `events` | Eventos narrativos | `idx_events_topo`, `idx_events_forced` |
| `event_edges` | **DAG causal** | `idx_edges_both` (único), `idx_edges_cause`, `idx_edges_effect` |
| `entity_deltas` | Cambios en entidades | `idx_entity_deltas_event` |
| `world_variable_deltas` | Cambios en variables globales | — |
| `dramatic_states` | Vector de 7 medidores | `idx_dramatic_commit` |
| `dramatic_deltas` | Historial dramático (paper) | `idx_dramatic_deltas_meter` |

---

## Uso básico

### Ejemplo: Guardar un mundo y commits

```python
import asyncio
from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.models.commit import NarrativeCommit
from persistence.database import DatabaseConfig
from persistence.repositories.postgresql_repository import PostgreSQLRepository

async def main():
    # 1. Configurar DB
    db_config = DatabaseConfig(
        "postgresql+asyncpg://cne_user:cne_password_dev@localhost:5432/cne_db"
    )
    repo = PostgreSQLRepository(db_config)

    # 2. Crear mundo
    hero = Entity(
        name="Aldric",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100, "courage": 80}
    )

    world = WorldDefinition(
        name="El Reino de las Sombras",
        context="Un reino medieval donde la magia oscura amenaza...",
        protagonist="Aldric, un caballero desterrado",
        era="Medieval fantástico",
        tone=NarrativeTone.DARK,
        initial_entities=[hero]
    )

    # 3. Guardar
    await repo.save_world(world)

    # 4. Crear commit inicial
    commit = NarrativeCommit(
        world_id=world.id,
        event_id="event_0",
        depth=0,
        narrative_text="El reino está en peligro...",
        summary="La historia comienza."
    )
    await repo.save_commit(commit)

    # 5. Guardar estado dramático
    await repo.save_dramatic_state(commit.id, world.dramatic_config)

    print(f"✅ Mundo guardado: {world.id}")
    print(f"✅ Commit guardado: {commit.id}")

    # Cleanup
    await db_config.dispose()

if __name__ == "__main__":
    asyncio.run(main())
```

### Ejemplo: Validar ciclos causales

```python
from cne_core.models.event import CausalEdge

async def validate_edge(repo):
    # Intentar crear A→B→A debe fallar
    edge_ab = CausalEdge(cause_event_id="A", effect_event_id="B")
    await repo.save_causal_edge(edge_ab)  # OK

    edge_ba = CausalEdge(cause_event_id="B", effect_event_id="A")
    try:
        await repo.save_causal_edge(edge_ba)  # FALLA
    except ValueError as e:
        print(f"❌ Ciclo detectado: {e}")
```

---

## Explorar la DB con Adminer

1. Ir a `http://localhost:8080`
2. Login:
   - **Sistema**: PostgreSQL
   - **Servidor**: `postgres`
   - **Usuario**: `cne_user`
   - **Contraseña**: `cne_password_dev`
   - **Base de datos**: `cne_db`
3. Explorar tablas, ejecutar queries, ver datos

---

## Queries útiles

### Ver el grafo causal completo

```sql
SELECT
    e1.summary AS causa,
    e2.summary AS efecto,
    edge.relation_type
FROM event_edges edge
JOIN events e1 ON edge.cause_event_id = e1.id
JOIN events e2 ON edge.effect_event_id = e2.id
ORDER BY e1.depth, e2.depth;
```

### Verificar ciclos manualmente (CTE recursiva)

```sql
WITH RECURSIVE causal_path AS (
    SELECT cause_event_id, effect_event_id, 1 AS depth
    FROM event_edges
    WHERE cause_event_id = '<event_id_inicial>'

    UNION

    SELECT e.cause_event_id, e.effect_event_id, p.depth + 1
    FROM event_edges e
    JOIN causal_path p ON e.cause_event_id = p.effect_event_id
    WHERE p.depth < 100
)
SELECT * FROM causal_path;
```

### Ver arco dramático de una historia

```sql
SELECT
    c.depth,
    c.summary,
    ds.tension,
    ds.hope,
    ds.chaos,
    ds.forced_event
FROM commits c
JOIN dramatic_states ds ON c.id = ds.commit_id
WHERE c.world_id = '<world_id>'
ORDER BY c.depth;
```

---

## Troubleshooting

### Error: "could not connect to server"

```bash
# Verificar que PostgreSQL esté corriendo
docker ps | grep postgres

# Ver logs
docker-compose logs postgres

# Reiniciar contenedor
docker-compose restart postgres
```

### Error: "relation does not exist"

```bash
# Verificar migraciones aplicadas
alembic current

# Si no hay migraciones, aplicarlas
alembic upgrade head

# Si hay problemas, resetear y recrear
alembic downgrade base
alembic upgrade head
```

### Error en tests: "database is being accessed by other users"

```bash
# Cerrar todas las conexiones a la DB
docker-compose restart postgres

# O conectarse con psql y forzar desconexión
docker exec -it cne_postgres psql -U cne_user -d cne_db
# Dentro de psql:
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'cne_db' AND pid <> pg_backend_pid();
```

### Limpiar todo y empezar de nuevo

```bash
# Detener y borrar volúmenes (RESETEA LA DB)
docker-compose down -v

# Levantar de nuevo
docker-compose up -d

# Aplicar migraciones
alembic upgrade head
```

---

## Siguiente paso: Fase 3 — AI Adapter

En Fase 3 vamos a:
- Implementar `AIAdapter` para Anthropic (Claude)
- Implementar `MockAIAdapter` para tests sin API key
- Crear `ContextBuilder` que construye el tronco activo
- Crear `ResponseValidator` que valida el JSON de la IA
- Integrar el motor completo: Core + Persistencia + IA

---

## Diferencias entre Fase 1 y Fase 2

| Aspecto | Fase 1 | Fase 2 |
|---------|--------|--------|
| Persistencia | En memoria (dicts) | PostgreSQL con SQLAlchemy async |
| Estado | Snapshots completos en cada commit | Snapshots + deltas (optimizado) |
| Validación causal | BFS en memoria | CTE recursiva en SQL |
| Tests | `test_fase1.py` (sin deps) | `test_fase2.py` (requiere Docker) |
| Ramas | Navegables en memoria | Persistidas con metadata |
| Performance | Rápido, limitado por RAM | Escalable, limitado por DB |

---

## Comandos rápidos

```bash
# Desarrollo
docker-compose up -d           # Levantar servicios
alembic upgrade head           # Aplicar migraciones
pytest tests/test_fase2.py -v # Ejecutar tests

# Exploración
docker-compose logs -f postgres    # Ver logs
docker exec -it cne_postgres psql -U cne_user -d cne_db  # Conectar a psql
open http://localhost:8080         # Abrir Adminer

# Limpieza
docker-compose down            # Detener servicios
docker-compose down -v         # Detener y borrar datos
```
