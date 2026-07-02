# Guia: Persistencia — SQLAlchemy, Alembic y PostgreSQL

> Si sabes SQL basico pero nunca has usado un ORM, esta guia te lleva desde
> cero hasta entender toda la capa de persistencia del CNE.

---

## 1. Que es un ORM

Un **ORM** (Object-Relational Mapping) traduce entre tablas SQL y objetos Python.
En lugar de escribir SQL a mano:

```sql
INSERT INTO worlds (id, name, context) VALUES ('abc-123', 'Valdris', 'Un reino...');
```

Escribes Python:

```python
session.add(WorldORM(id="abc-123", name="Valdris", context="Un reino..."))
await session.commit()
```

El ORM genera el SQL por ti. Ventajas: evita inyeccion SQL, refactorizable con
el IDE, y agnostico de base de datos (cambiando solo la URL de conexion).
En este proyecto usamos **SQLAlchemy 2.0**.

## 2. SQLAlchemy 2.0 Async

Las queries son **I/O-bound**: el servidor espera a que PostgreSQL responda.
Con `async`, el servidor atiende otras peticiones HTTP mientras espera.

**Cadena de conexion:**
```
postgresql+asyncpg://cne_user:cne_password@localhost:5433/cne_db
│           │         │          │            │          └─ base de datos
│           └─ driver async      └─ password  └─ host:puerto
└─ dialecto (PostgreSQL)
```

Ejemplo real de `persistence/database.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

class DatabaseConfig:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            pool_pre_ping=True,   # Verifica conexiones antes de usarlas
            pool_size=10,         # Mantiene 10 conexiones abiertas
            max_overflow=20,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False,
        )
```

Cada request HTTP recibe su propia sesion via `get_session()`, con commit
automatico al finalizar y rollback en caso de excepcion.

## 3. ORM Models del proyecto

El proyecto separa los modelos de dominio (dataclasses en `cne_core/models/`)
de los ORM models (en `persistence/models/`). El Core Engine no depende de
SQLAlchemy.

| Dominio (`cne_core/`) | ORM (`persistence/models/`) | Tabla |
|---|---|---|
| `WorldDefinition` | `WorldORM` | `worlds` |
| `Entity` | `EntityORM` | `entities` |
| `NarrativeEvent` | `EventORM` | `events` |
| `CausalEdge` | `CausalEdgeORM` | `event_edges` |
| `NarrativeCommit` | `CommitORM` | `commits` |
| `Branch` | `BranchORM` | `branches` |
| `NarrativeChoice` | `ChoiceORM` | `choices` |
| *(vector dramatico)* | `DramaticStateORM` | `dramatic_states` |

Los ORM models viven en 3 archivos: `world_orm.py`, `event_orm.py`, `commit_orm.py`.
Todos heredan de `Base` (la base declarativa de SQLAlchemy en `persistence/database.py`).

Ejemplo simplificado de `WorldORM`:

```python
class WorldORM(Base):
    __tablename__ = "worlds"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    dramatic_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    entities: Mapped[list["EntityORM"]] = relationship(
        "EntityORM", back_populates="world", cascade="all, delete-orphan"
    )
```

Para entender los dataclasses del dominio, lee `guia_python.md`.

## 4. Relaciones entre tablas

**ForeignKey** conecta tablas. En `EntityORM`, `world_id` apunta a `worlds`:

```python
world_id: Mapped[str] = mapped_column(
    String(36), ForeignKey("worlds.id", ondelete="CASCADE")
)
```

`ondelete="CASCADE"`: si borras un mundo, PostgreSQL borra sus entidades.

**relationship()** permite acceder a objetos relacionados desde Python:

```python
# En WorldORM: un mundo tiene muchas entidades
entities = relationship("EntityORM", back_populates="world", cascade="all, delete-orphan")

# En EntityORM: cada entidad pertenece a un mundo
world = relationship("WorldORM", back_populates="entities")
```

**selectinload()** carga relaciones en una sola query extra, evitando el
problema N+1 (sin el, acceder a `world.entities` en un loop dispara una
query por cada mundo):

```python
select(WorldORM).options(selectinload(WorldORM.entities)).where(WorldORM.id == world_id)
```

## 5. Queries comunes

Ejemplos reales de `persistence/repositories/postgresql_repository.py`:

```python
# SELECT con filtro
result = await session.execute(
    select(WorldORM).options(selectinload(WorldORM.entities))
    .where(WorldORM.id == world_id)
)
world = result.scalar_one_or_none()   # Retorna None si no existe

# INSERT
session.add(WorldORM(id=world.id, name=world.name, context=world.context, ...))
await session.flush()   # Envia a la BD sin hacer commit todavia

# DELETE (CASCADE borra entidades, commits, etc.)
await session.delete(world_orm)
await session.flush()

# SELECT con ORDER BY + LIMIT
result = await session.execute(
    select(WorldORM).order_by(WorldORM.created_at.desc()).limit(50)
)
worlds = result.scalars().all()

# Eager loading de multiples relaciones
result = await session.execute(
    select(CommitORM).options(
        selectinload(CommitORM.dramatic_state),
        selectinload(CommitORM.events),
        selectinload(CommitORM.choices),
    ).where(CommitORM.id == commit_id)
)
```

## 6. Alembic: migraciones de base de datos

Cuando cambias un modelo ORM, la base de datos **no se actualiza sola**.
Una migracion es un script Python que ejecuta el `ALTER TABLE` correspondiente.

Cada migracion tiene un ID unico, sabe cual es la anterior (`down_revision`),
y define `upgrade()` y `downgrade()`.

### Las 4 migraciones del proyecto

| Archivo | Que hace |
|---|---|
| `001_initial_schema.py` | Crea las 10 tablas base con indices y constraints |
| `002_add_choices_table.py` | Agrega la tabla `choices` |
| `003_add_causal_reason_to_events.py` | Agrega columna `causal_reason` a `events` |
| `004_entity_creations_table.py` | Crea tabla de auditoria `entity_creations` |

Ejemplo completo — migracion 003 (agrega una columna):

```python
from alembic import op
import sqlalchemy as sa

revision = '003_add_causal_reason'
down_revision = '002_add_choices_table'

def upgrade() -> None:
    op.add_column('events', sa.Column('causal_reason', sa.Text, nullable=True))

def downgrade() -> None:
    op.drop_column('events', 'causal_reason')
```

## 7. Comandos de Alembic

```bash
alembic upgrade head            # Aplicar TODAS las migraciones pendientes
alembic downgrade -1            # Revertir la ultima migracion
alembic current                 # Ver que migracion esta aplicada
alembic history                 # Ver historial de migraciones
alembic revision --autogenerate -m "descripcion"  # Crear nueva migracion
```

**Flujo tipico** al agregar una columna: (1) agregas el campo al ORM model,
(2) ejecutas `alembic revision --autogenerate -m "..."`, (3) revisas el
archivo generado, (4) ejecutas `alembic upgrade head`.

## 8. CTE recursiva para validacion causal

`persistence/queries/causal_queries.py` contiene la query mas critica del
proyecto: verificar que el DAG causal no tenga ciclos. Antes de insertar una
arista `A -> B`, se verifica que no exista un camino `B -> ... -> A`:

```sql
WITH RECURSIVE causal_path AS (
    SELECT cause_event_id, effect_event_id, 1 AS depth
    FROM event_edges
    WHERE cause_event_id = :from_event_id
    UNION
    SELECT e.cause_event_id, e.effect_event_id, p.depth + 1
    FROM event_edges e
    INNER JOIN causal_path p ON e.cause_event_id = p.effect_event_id
    WHERE p.depth < 100
)
SELECT 1 FROM causal_path WHERE effect_event_id = :to_event_id LIMIT 1
```

Esta CTE es el equivalente SQL del BFS que `CausalValidator` hace en memoria.
La version SQL opera directamente sobre la base de datos sin cargar el grafo
completo a memoria.

## 9. Pruebalo tu mismo

```bash
# 1. Levantar PostgreSQL (ver guia_docker.md)
docker-compose up -d postgres

# 2. Aplicar todas las migraciones
alembic upgrade head

# 3. Explorar tablas con Adminer (http://localhost:8080)
#    Servidor: postgres | Usuario: cne_user | Password: cne_password | BD: cne_db
docker-compose up -d adminer

# 4. Ver historial de migraciones
alembic history

# 5. Inspeccionar una migracion sencilla
#    Abre: migrations/versions/003_add_causal_reason_to_events.py
```

Para levantar PostgreSQL con Docker, lee `guia_docker.md`.

---

**Siguiente lectura**: `guia_arquitectura.md` explica como estas capas
se conectan en la arquitectura general del CNE.
