# Causal Narrative Engine (CNE) — Árbol Literario

> **Contexto para Claude Code**: Este archivo es el punto de entrada completo
> del proyecto. Lee esto antes de tocar cualquier archivo de código.

---

## ¿Qué es este proyecto?

Un **motor narrativo independiente** basado en causalidad formal para generar
historias ramificadas con IA manteniendo coherencia verificable. El objetivo
es construir el motor como un framework reutilizable que cualquier proyecto
pueda integrar — un juego, una herramienta de escritura, una API, o un pipeline
de generación de contenido.

**El motor es el producto.** Los clientes (interfaces, juegos, aplicaciones)
son responsabilidad de quien lo integre. Este repositorio no implementa
ningún cliente específico.

Objetivos concretos:
1. **Motor independiente**: `pip install cne-core` y funciona. Sin acoplamientos a ningún framework de UI, base de datos específica, o proveedor de IA.
2. **Extensible por diseño**: interfaces abstractas para persistencia y IA permiten swappear implementaciones sin tocar el core.
3. **Paper académico**: publicar el framework como investigación en narrativa computacional (target: AIIDE / IEEE CoG).

El nombre original del concepto es **Árbol Literario** — una metáfora estructural
donde cada componente del árbol tiene un equivalente formal en el sistema.

---

## Modelo Formal

```
CNE = (W, E, S, D, T, C, Φ)
```

| Símbolo | Nombre | Descripción |
|---------|--------|-------------|
| `W` | WorldDefinition | Semilla inmutable: género, tono, reglas, restricciones |
| `E` | Event Space | Todos los eventos narrativos posibles |
| `S(t)` | Narrative State | `(Entities(t), WorldVars(t), D(t), History(t))` |
| `D(t)` | Dramatic Vector | `(tension, hope, chaos, rhythm, saturation, connection, mystery) ∈ [0,100]⁷` |
| `T` | Transition Function | `S(t+1) = T(S(t), choice, proposal_IA)` |
| `C` | Causal Graph | DAG dirigido de eventos. Sin ciclos. |
| `Φ` | Dramatic Function | Evalúa umbrales de D(t) → ForcedEventConstraint \| None |

**Función de transición extendida:**
```
T(S(t), choice, ε) = C(V(G(S(t), choice, ε)), Φ(D(t)))
```
- `G` = generación estocástica (IA propone)
- `V` = validación (motor verifica coherencia causal)
- `Φ` = evaluación dramática (umbrales → eventos forzados)
- `C` = commit determinista (persistencia + actualización de estado)

**4 propiedades garantizadas:**
- **P1 Causalidad**: el grafo de eventos es siempre un DAG (sin ciclos)
- **P2 Determinismo**: `S(t)` es reconstruible desde snapshots + deltas
- **P3 Versionado**: cada decisión = commit con parent_id (árbol Git-like)
- **P4 Consistencia**: entidades muertas no actúan, variables en rango válido

---

## Árbol Literario → Equivalentes Formales

| Metáfora | Equivalente técnico |
|----------|---------------------|
| Semilla | `WorldDefinition` — inmutable, define el universo |
| Raíces | `Entity` registry + world variables (parámetros estructurales) |
| Tronco/Tallo | Narrative trunk: DAG de commits causales |
| Hojas | `NarrativeChoice` — opciones generadas por IA, validadas por motor |
| Ramas | `Branch` — caminos elegidos, navigables hacia atrás |
| Vitalidad | `DramaticVector` — reemplaza "vida del árbol" con 7 medidores |

---

## Sistema Dramático Multi-Medidor (SDMM)

El SDMM es la innovación central del proyecto. Reemplaza el concepto intuitivo
de "vida del árbol" con un vector formal de 7 dimensiones.

### Los 7 Medidores

| Medidor | Rango | Inicio típico | Qué mide |
|---------|-------|---------------|----------|
| `tension` | [0-100] | 30 | Nivel de conflicto activo |
| `hope` | [0-100] | 60 | Percepción de que las cosas pueden mejorar |
| `chaos` | [0-100] | 20 | Entropía del mundo, eventos impredecibles |
| `rhythm` | [0-100] | 50 | Velocidad narrativa |
| `saturation` | [0-100] | 0 | Agotamiento del arco actual |
| `connection` | [0-100] | 40 | Profundidad emocional con personajes |
| `mystery` | [0-100] | 50 | Preguntas sin resolver |

### Interacciones entre medidores (se aplican automáticamente)

```
tension > 50  →  hope -= ((tension - 50) // 10) * 2
chaos > 60    →  rhythm += (chaos - 60) // 10
saturation > 70  →  connection -= (saturation - 70) // 5
hope < 20     →  mystery += 3
```

### Umbrales → Eventos Forzados (Φ)

```python
# Prioridad 1: combinaciones
mystery > 65 AND tension > 65  →  CLIMAX_REVELATION
connection > 70 AND tension > 60  →  EMOTIONAL_MOMENT

# Prioridad 2: individuales
saturation > 95  →  ARC_CLOSURE
tension > 85     →  CLIMAX
hope < 10        →  TRAGEDY
chaos > 80       →  CHAOS_STORM
saturation > 85  →  PLOT_TWIST
tension < 15     →  DISRUPTIVE
hope > 90        →  UNEXPECTED_THREAT
rhythm > 90 (×3 turnos)  →  NARRATIVE_REST
```

Cuando se fuerza un evento, la IA recibe un **constraint obligatorio** en el
system prompt. El evento se integra causalmente al DAG — no es una interrupción
externa sino una consecuencia formal de los eventos que elevaron el medidor.

---

## Arquitectura: Capas Independientes

```
┌──────────────────────────────────────────────────────┐
│              Cualquier cliente externo               │
│   (juego, API, CLI, herramienta de escritura, etc.)  │
│           → responsabilidad del integrador           │
└─────────────────────┬────────────────────────────────┘
                      │ import cne_core  /  HTTP  /  SDK
┌─────────────────────▼────────────────────────────────┐
│            FastAPI REST (Fase 4)                     │
│    Expone el motor como servicio HTTP consumible     │
│    por cualquier cliente en cualquier lenguaje       │
└─────────────────────┬────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────┐
│           Core Engine  —  cne_core/                  │
│   CausalValidator  │  DramaticEngine  │  StateMachine│
│   ContextBuilder   │  NarrativeRunner │  Interfaces  │
└──────────┬──────────────────────────────┬────────────┘
           │                              │
┌──────────▼──────────┐      ┌────────────▼────────────┐
│  Persistence Layer  │      │      AI Adapter          │
│  (Fase 2)           │      │      (Fase 3)            │
│                     │      │                          │
│  Interface ABC      │      │  Interface ABC           │
│  ─────────────      │      │  ─────────────           │
│  PostgreSQL impl.   │      │  Anthropic impl.         │
│  SQLite impl.       │      │  OpenAI impl.            │
│  InMemory impl. ✅  │      │  Local LLM impl.         │
│  JSON impl.         │      │  Mock impl. ✅           │
└─────────────────────┘      └──────────────────────────┘
```

**Principio clave**: la coherencia es propiedad estructural del motor, NO del LLM.
La IA es un generador de propuestas. El motor es el árbitro.

**Principio de extensibilidad**: el Core Engine solo conoce interfaces (`ABC`).
Cualquier implementación concreta de persistencia o IA es intercambiable
sin modificar una sola línea del core. Esto es lo que hace el motor
independientemente reutilizable.

---

## Estado Actual del Proyecto

### ✅ FASE 1 COMPLETADA — Core Engine (Python puro, sin dependencias externas)

**Archivos implementados:**

```
cne_core/
├── models/
│   ├── world.py       # WorldDefinition, Entity, EntityType, NarrativeTone
│   ├── event.py       # NarrativeEvent, CausalEdge, EntityDelta,
│   │                  # WorldVariableDelta, DramaticDelta
│   └── commit.py      # NarrativeCommit, Branch, NarrativeChoice
├── engine/
│   ├── causal_validator.py  # CausalValidator: detección de ciclos DAG (BFS)
│   ├── dramatic_engine.py   # DramaticEngine: SDMM completo con Φ
│   └── state_machine.py     # StateMachine: orquestador en memoria
tests/
└── test_fase1.py      # Tests completos, todas las propiedades verificadas
```

**Resultado de tests:**
```
✅ P1 CAUSALIDAD:   DAG válido, ciclos detectados correctamente
✅ P2 DETERMINISMO: Estado reconstruible, go_to_commit() funciona
✅ P3 VERSIONADO:   Ramas alternativas navegables
✅ P4 CONSISTENCIA: Entidades mueren, variables actualizadas
✅ DRAMATIC ENGINE: Umbrales y eventos forzados funcionan
```

---

### 🔲 FASE 2 — Persistencia (SIGUIENTE)

**Objetivo**: misma lógica del Core Engine, pero persistida en PostgreSQL.

**Stack**: SQLAlchemy 2.0 (async) + Alembic + PostgreSQL 16+

**Lo que hay que construir:**

#### Nuevas tablas SQL (además de las del diseño original):

```sql
-- Vector dramático por commit
CREATE TABLE dramatic_state (
    id              UUID PRIMARY KEY,
    commit_id       UUID NOT NULL REFERENCES narrative_commits(id),
    tension         SMALLINT NOT NULL DEFAULT 30 CHECK (tension BETWEEN 0 AND 100),
    hope            SMALLINT NOT NULL DEFAULT 60 CHECK (hope BETWEEN 0 AND 100),
    chaos           SMALLINT NOT NULL DEFAULT 20 CHECK (chaos BETWEEN 0 AND 100),
    rhythm          SMALLINT NOT NULL DEFAULT 50 CHECK (rhythm BETWEEN 0 AND 100),
    saturation      SMALLINT NOT NULL DEFAULT 0  CHECK (saturation BETWEEN 0 AND 100),
    connection      SMALLINT NOT NULL DEFAULT 40 CHECK (connection BETWEEN 0 AND 100),
    mystery         SMALLINT NOT NULL DEFAULT 50 CHECK (mystery BETWEEN 0 AND 100),
    forced_event    TEXT,
    trigger_meter   TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Historial de cambios en medidores (para el paper)
CREATE TABLE dramatic_state_deltas (
    id          UUID PRIMARY KEY,
    event_id    UUID NOT NULL REFERENCES events(id),
    meter       TEXT NOT NULL,
    delta       SMALLINT NOT NULL,
    reason      TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### Interfaces abstractas (Repository pattern):

```python
# El Core Engine NO habla directamente con PostgreSQL.
# Habla con estas interfaces. Eso hace el sistema replicable.

class NarrativeRepository(ABC):
    @abstractmethod
    async def save_commit(self, commit: NarrativeCommit) -> None: ...

    @abstractmethod
    async def get_commit(self, commit_id: str) -> NarrativeCommit | None: ...

    @abstractmethod
    async def get_trunk(self, commit_id: str, max_depth: int) -> list[NarrativeCommit]: ...

    @abstractmethod
    async def save_event(self, event: NarrativeEvent) -> None: ...

    @abstractmethod
    async def save_dramatic_state(self, commit_id: str, vector: dict) -> None: ...

    @abstractmethod
    async def get_entity_state(self, entity_id: str, at_commit: str) -> dict: ...

class AIAdapter(ABC):
    @abstractmethod
    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal: ...
```

#### Validación causal en SQL (CTE recursiva):

```sql
-- Antes de insertar arista A→B, verificar que no exista B→...→A
WITH RECURSIVE path AS (
    SELECT parent_event_id, child_event_id
    FROM event_edges
    WHERE parent_event_id = $child_event   -- empieza desde B

    UNION

    SELECT e.parent_event_id, e.child_event_id
    FROM event_edges e
    JOIN path p ON e.parent_event_id = p.child_event_id
)
SELECT 1 FROM path WHERE child_event_id = $parent_event LIMIT 1;
-- Si retorna fila → hay ciclo → rechazar
```

#### StateRebuilder:

```python
# Reconstruye S(t) completo desde un commit dado
# Algoritmo: encuentra snapshot más cercano + aplica deltas acumulados
class StateRebuilder:
    async def rebuild_from_commit(
        self,
        commit_id: str,
        repo: NarrativeRepository
    ) -> WorldState:
        snapshot = await repo.get_nearest_snapshot(commit_id)
        deltas   = await repo.get_deltas_since(snapshot.commit_id, commit_id)
        return self._apply_deltas(snapshot.state, deltas)
```

**Archivos a crear en Fase 2:**

```
cne_core/
├── interfaces/
│   ├── repository.py      # NarrativeRepository ABC
│   └── ai_adapter.py      # AIAdapter ABC
persistence/
├── models/                # SQLAlchemy ORM models (mapean los dataclasses)
│   ├── world_orm.py
│   ├── event_orm.py
│   └── commit_orm.py
├── repositories/          # Implementaciones concretas PostgreSQL
│   ├── world_repository.py
│   ├── event_repository.py
│   ├── commit_repository.py
│   └── dramatic_repository.py
├── queries/
│   └── causal_queries.py  # CTE recursiva + topological order
└── state_rebuilder.py     # Reconstrucción de estado desde deltas
migrations/
└── versions/
    └── 001_initial_schema.py   # Alembic migration
docker-compose.yml             # motor + PostgreSQL + Redis
```

---

### 🔲 FASE 3 — AI Adapter

**Contrato JSON que la IA debe retornar** (validado por ResponseValidator):

```json
{
  "narrative": "Texto inmersivo 150-250 palabras",
  "summary": "Resumen causal de 1 oración para el tronco",
  "choices": ["opción A", "opción B", "opción C"],
  "choice_dramatic_preview": [
    { "choice": "opción A", "tension_delta": 15, "hope_delta": -10, "tone": "confrontacional" },
    { "choice": "opción B", "tension_delta": -5, "hope_delta": 5,   "tone": "diplomático" },
    { "choice": "opción C", "tension_delta": 5,  "hope_delta": 10,  "tone": "inesperado" }
  ],
  "entity_deltas": [{"entity_id": "uuid", "attribute": "health", "old_value": 100, "new_value": 85}],
  "world_deltas":  [{"variable": "political_stability", "old_value": 60, "new_value": 48}],
  "dramatic_deltas": {
    "tension": 15, "hope": -8, "chaos": 5,
    "rhythm": 0, "saturation": 8, "connection": -3, "mystery": 10
  },
  "causal_reason": "Por qué este evento ocurre dado el estado actual",
  "forced_event_type": null,
  "is_ending": false
}
```

**Tronco activo** (~1500 tokens máximo, independiente de la longitud de la historia):

```
SEMILLA DEL MUNDO:
[WorldDefinition.to_context_string()]

ESTADO DRAMÁTICO ACTUAL:
Tensión: 78/100 🔴
Esperanza: 41/100 🔴
[...resto del vector...]

HISTORIA ANTERIOR (comprimida):
• [Cap.0] El rey Aldric muere misteriosamente (T=50, H=55)
• [Cap.1] → "Investigación secreta" | Lyra encarga investigar a Sera (T=58)

CAPÍTULOS RECIENTES (últimos 6, con detalle):
[Cap.2] → "Seguir a Malachar" | Lyra descubre la conspiración (T=78, H=41)

[CONSTRAINT DRAMÁTICO OBLIGATORIO — si Φ detectó umbral]
⚠️ La tensión ha llegado a su punto máximo. DEBE ocurrir un clímax...
```

---

### 🔲 FASE 4 — FastAPI REST + SDK Python

**Objetivo**: exponer el motor de dos formas para máxima portabilidad:

**A) API REST** — para clientes en cualquier lenguaje:
```
POST   /worlds                       # Crear WorldDefinition (semilla)
GET    /worlds/{world_id}            # Obtener mundo
POST   /worlds/{world_id}/start      # Iniciar historia → primer NarrativeCommit
POST   /commits/{commit_id}/advance  # Tomar decisión → nuevo commit
GET    /commits/{commit_id}/state    # Estado actual del mundo
GET    /commits/{commit_id}/dramatic_state   # Vector dramático
GET    /worlds/{world_id}/branches   # Árbol de ramas navegable
POST   /commits/{commit_id}/goto     # Regresar a un commit anterior
```

**B) SDK Python** — para integración directa sin HTTP:
```python
# Uso objetivo: instalar y usar en 5 líneas
from cne_core import NarrativeEngine, WorldDefinition

engine = NarrativeEngine.from_config("config.json")
result = await engine.start(world)
result = await engine.advance(commit_id, choice="atacar al guardia")
```

El SDK es `cne_core` directamente — quien quiera integrarlo en Python
importa el paquete sin necesidad de levantar una API.

---

### 🔲 FASE 5 — Documentación y Release Open Source

**Objetivo**: hacer el motor genuinamente usable por otros sin asistencia.

```
docs/
├── quickstart.md          # Motor funcionando en < 10 minutos
├── concepts.md            # Árbol Literario, SDMM, causalidad formal
├── api_reference.md       # Documentación completa de la API REST
├── sdk_reference.md       # Documentación del SDK Python
├── extending.md           # Cómo implementar AIAdapter y Repository propios
├── examples/
│   ├── minimal/           # Historia de 3 decisiones, InMemory + MockAI
│   ├── with_postgres/     # Con PostgreSQL real
│   └── with_claude_api/   # Con Anthropic SDK
└── paper/                 # Documentación académica
```

**Entregables**:
- `pyproject.toml` listo para publicar en PyPI como `cne-core`
- GitHub release con changelog
- README con ejemplos copy-paste funcionales
- Docker image pública: `ghcr.io/usuario/cne:latest`

---

### 🔲 FASE 6 — Paper Académico

---

## Convenciones de Código

### Nombrado
```python
# Clases: PascalCase
class NarrativeCommit: ...
class DramaticEngine: ...

# Métodos y variables: snake_case
def advance_story(...): ...
current_commit_id = "..."

# Constantes y enums: UPPER_SNAKE o PascalCase para Enum
class ForcedEventType(str, Enum):
    CLIMAX = "CLIMAX"

# IDs siempre como str (UUID serializable)
id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

### Patrones establecidos
- **Dataclasses** para todos los modelos de dominio (`@dataclass`)
- **`str` + `Enum`** para todos los enums (serializables a JSON directamente)
- **`field(default_factory=...)`** para defaults mutables (listas, dicts)
- **`property`** para lógica derivada que se lee como atributo (`is_alive`, `is_root`)
- **`ABC`** para interfaces (Repository, AIAdapter) — no implementar en Core
- **Async** en Fase 2+ (SQLAlchemy 2.0 async) — el Core Engine es síncrono

### Errores
```python
# Errores específicos del dominio, nunca Exception genérico
class CausalCycleError(Exception): ...
class EventNotFoundError(Exception): ...
class ValidationError(Exception): ...   # (Fase 3)
```

### Testing
```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Ejecutar solo Fase 1
python tests/test_fase1.py

# El test de Fase 1 NO requiere dependencias externas
# (sin PostgreSQL, sin API keys, sin Docker)
```

---

## Dependencias por Fase

```toml
# Fase 1 (actual) — CERO dependencias externas
# Solo Python 3.11+ stdlib

# Fase 2 — Persistencia
sqlalchemy = "^2.0"
alembic = "^1.13"
asyncpg = "^0.29"        # driver async para PostgreSQL
psycopg2-binary = "^2.9"

# Fase 3 — IA
anthropic = "^0.30"
pydantic = "^2.0"        # validación del contrato JSON

# Fase 4 — API + SDK
fastapi = "^0.110"
uvicorn = "^0.29"
# El SDK es cne_core mismo — sin dependencias adicionales

# Fase 5 — Packaging
build = "^1.0"           # para publicar en PyPI
twine = "^5.0"

# Dev
pytest = "^8.0"
pytest-asyncio = "^0.23"
```

### Implementaciones opcionales incluidas en el repo

El motor viene con implementaciones de referencia intercambiables:

| Componente | Implementación | Cuándo usar |
|------------|---------------|-------------|
| Repository | `InMemoryRepository` ✅ | Tests, prototipos, demos |
| Repository | `PostgreSQLRepository` | Producción, historias largas |
| Repository | `SQLiteRepository` | Desarrollo local sin Docker |
| AIAdapter | `MockAIAdapter` ✅ | Tests sin API key |
| AIAdapter | `AnthropicAdapter` | Producción con Claude |
| AIAdapter | `OpenAIAdapter` | Alternativa GPT |
| AIAdapter | `LocalLLMAdapter` | Ollama / LLMs locales |

---

## Métricas Formales (para el paper)

| Métrica | Símbolo | Definición |
|---------|---------|------------|
| Causal Consistency Score | CCS | Proporción de eventos con al menos una causa registrada |
| Entity Coherence Rate | ECR | Proporción de referencias a entidades consistentes con su estado |
| Dramatic Arc Fidelity | DAF | Similitud entre arco de tensión generado y arco de referencia (3 actos) |
| Threshold Trigger Rate | TTR | Eventos iniciados por SDMM vs decisiones del jugador |
| Context Efficiency | CE | tokens_contexto / eventos_historia |

---

## Contribuciones Originales al Paper

1. **Literary Tree Model**: formalización del Árbol Literario como sistema de transición de estados con DAG causal
2. **Dramatic Vector Formalism (DVF)**: vector de 7 dimensiones como subelemento formal del estado narrativo
3. **Threshold-Driven Narrative Control (TDNC)**: eventos forzados por umbrales que se integran causalmente al DAG
4. **Active Trunk Compression**: método de compresión de contexto narrativo para LLMs preservando coherencia
5. **Coherence as Structural Property**: arquitectura donde coherencia ≠ capacidad del LLM sino propiedad del motor
6. **Narrative Git Versioning**: versionado tipo Git de decisiones narrativas con reconstrucción determinista

---

## Comandos Útiles

```bash
# Verificar que el Core Engine funciona
python tests/test_fase1.py

# Estructura del proyecto
find . -name "*.py" | grep -v __pycache__ | sort

# Cuando llegues a Fase 2: levantar infraestructura
docker-compose up -d

# Cuando llegues a Fase 2: correr migraciones
alembic upgrade head
```

---

## Notas Importantes

- **No usar `vitality`** en el código — fue reemplazado por `DramaticVector`. Si ves referencias a `vitality` en documentos viejos, ignorarlas.
- **`StateMachine` en Fase 1 es síncrono** — en Fase 2 se convierte a `async` cuando use SQLAlchemy async.
- **El Core Engine nunca importa de `persistence/`** — la dependencia va en dirección opuesta.
- **La IA nunca modifica directamente el estado** — siempre propone, el motor valida y aplica.
- **`go_to_commit()` en Fase 1 restaura desde snapshots** — en Fase 2 usará `StateRebuilder` con deltas reales.
- **No acoplar el core a ningún cliente específico** — si una implementación del core requiere importar FastAPI, Flutter, o cualquier framework de UI, es un error de diseño.
- **Las interfaces ABC son el contrato público del motor** — `NarrativeRepository` y `AIAdapter` son lo que un integrador externo implementa para conectar su stack al CNE. Documentarlas bien es prioritario.
