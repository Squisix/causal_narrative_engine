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
| `S(t)` | Narrative State | `(Entities(t), EntityCreations(t), WorldVars(t), D(t), History(t))` |
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
│            FastAPI REST  ✅                          │
│    api/ — NarrativeServiceV2 + routers              │
└─────────────────────┬────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────┐
│           Core Engine  —  cne_core/                  │
│   CausalValidator  │  DramaticEngine  │  StateMachine│
│   ContextBuilder   │  ResponseSchema  │  Interfaces  │
└──────────┬──────────────────────────────┬────────────┘
           │                              │
┌──────────▼──────────┐      ┌────────────▼────────────┐
│  Persistence Layer  │      │      AI Adapter          │
│                     │      │                          │
│  Interface ABC      │      │  Interface ABC           │
│  ─────────────      │      │  ─────────────           │
│  PostgreSQL ✅      │      │  Anthropic ✅            │
│                     │      │  Ollama ✅               │
│                     │      │  Mock ✅                 │
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

### ✅ FASE 1 COMPLETADA — Core Engine

```
cne_core/
├── models/
│   ├── world.py       # WorldDefinition, Entity, EntityType, NarrativeTone
│   ├── event.py       # NarrativeEvent, CausalEdge, EntityDelta, EntityCreation,
│   │                  # WorldVariableDelta, DramaticDelta
│   └── commit.py      # NarrativeCommit, Branch, NarrativeChoice
├── engine/
│   ├── causal_validator.py  # CausalValidator: detección de ciclos DAG (BFS)
│   ├── dramatic_engine.py   # DramaticEngine: SDMM completo con Φ
│   └── state_machine.py     # StateMachine: orquestador en memoria
├── interfaces/
│   ├── repository.py        # NarrativeRepository ABC
│   └── ai_adapter.py        # AIAdapter ABC + NarrativeContext/NarrativeProposal
└── ai/
    ├── context_builder.py   # ContextBuilder: tronco activo para LLMs
    ├── response_schema.py   # NarrativeResponse (Pydantic) + to_core_models()
    └── response_validator.py # Validación del JSON de la IA
```

**4 propiedades verificadas:**
```
✅ P1 CAUSALIDAD:   DAG válido, ciclos detectados correctamente
✅ P2 DETERMINISMO: Estado reconstruible, go_to_commit() funciona
✅ P3 VERSIONADO:   Ramas alternativas navegables
✅ P4 CONSISTENCIA: Entidades mueren, variables actualizadas
✅ DRAMATIC ENGINE: Umbrales y eventos forzados funcionan
```

---

### ✅ FASE 2 COMPLETADA — Persistencia PostgreSQL

**Stack**: SQLAlchemy 2.0 (async) + Alembic + PostgreSQL 16+

```
persistence/
├── database.py                    # DatabaseConfig, async session factory
├── models/
│   ├── world_orm.py               # WorldORM, EntityORM
│   ├── event_orm.py               # EventORM, EntityDeltaORM, EntityCreationORM
│   └── commit_orm.py              # CommitORM, BranchORM, ChoiceORM, DramaticStateORM
├── repositories/
│   └── postgresql_repository.py   # PostgreSQLRepository (implementa NarrativeRepository)
└── queries/
    └── causal_queries.py          # CTE recursiva para validación causal en SQL

migrations/versions/
├── 001_initial_schema.py          # Tablas base (worlds, entities, events, commits, branches)
├── 002_add_choices_table.py       # Tabla choices
├── 003_add_causal_reason_to_events.py  # Campo causal_reason en events
└── 004_entity_creations_table.py  # Tabla entity_creations (auditoría)

docker-compose.yml                 # PostgreSQL + Ollama
```

---

### ✅ FASE 3 COMPLETADA — AI Adapter

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
  "entity_creations": [
    {"entity_name": "Nombre", "entity_type": "character|artifact|faction|location",
     "attributes": {"health": 100, "possessed_by": null, "location": "lugar", "usable": true, "effect": "desc"}}
  ],
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

**Adapters implementados:**

```
adapters/
├── mock_adapter.py         # MockAdapter: determinista, para tests
├── anthropic_adapter.py    # AnthropicAdapter: Claude API
└── ollama_adapter.py       # OllamaAdapter: LLMs locales gratuitos
```

**`to_core_models()` retorna 5-tuple:**
```python
entity_deltas, entity_creations, world_deltas, dramatic_delta, choices = response.to_core_models()
```

---

### ✅ FASE 4 COMPLETADA — FastAPI REST API

```
api/
├── main.py              # App FastAPI con routers
├── config.py            # Configuración del servidor
├── dependencies.py      # Inyección de dependencias (repo, service)
├── routers/
│   ├── worlds.py        # CRUD de mundos
│   ├── narrative.py     # start, advance, goto, commits
│   └── health.py        # Health check
├── services/
│   └── narrative_service_v2.py  # Orquestador con persistencia
└── models/
    ├── requests.py      # Pydantic request schemas
    └── responses.py     # Pydantic response schemas
```

**Endpoints:**
```
POST   /worlds                       # Crear WorldDefinition
GET    /worlds/{world_id}            # Obtener mundo
DELETE /worlds/{world_id}            # Eliminar mundo
POST   /worlds/{world_id}/start      # Iniciar historia
GET    /worlds/{world_id}/commits    # Listar commits
POST   /commits/{commit_id}/advance  # Tomar decisión
GET    /commits/{commit_id}          # Estado de un commit
GET    /commits/{commit_id}/dramatic # Vector dramático
POST   /commits/{commit_id}/goto     # Navegar a commit anterior
GET    /health                       # Estado del servidor
```

---

### 🔲 FASE 5 — Documentación y Release Open Source

**Objetivo**: hacer el motor genuinamente usable por otros sin asistencia.

**Entregables**:
- `pyproject.toml` listo para publicar en PyPI como `cne-core`
- GitHub release con changelog
- Documentación completa (quickstart, API reference, extending guide)
- Docker image pública

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

### Implementaciones incluidas en el repo

| Componente | Implementación | Estado | Cuándo usar |
|------------|---------------|--------|-------------|
| Repository | `PostgreSQLRepository` | ✅ | Producción y tests de integración |
| AIAdapter | `MockAdapter` | ✅ | Tests sin API key (determinista) |
| AIAdapter | `AnthropicAdapter` | ✅ | Producción con Claude |
| AIAdapter | `OllamaAdapter` | ✅ | LLMs locales gratuitos (gemma3, llama, etc.) |

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
# Core Engine (sin dependencias)
python tests/test_fase1.py

# Todos los tests (requiere Docker + PostgreSQL)
docker-compose up -d
alembic upgrade head
pytest tests/ -v

# Tests sin Docker (solo core + adapters)
pytest tests/test_fase1.py tests/test_adapters.py -v

# Levantar API REST
uvicorn api.main:app --reload --port 8000
```

---

## Notas Importantes

- **No usar `vitality`** en el código — fue reemplazado por `DramaticVector`. Si ves referencias a `vitality` en documentos viejos, ignorarlas.
- **`StateMachine` es síncrono** — la capa async vive en `NarrativeServiceV2` que orquesta engine + repository + adapter.
- **El Core Engine nunca importa de `persistence/`** — la dependencia va en dirección opuesta.
- **La IA nunca modifica directamente el estado** — siempre propone, el motor valida y aplica.
- **`go_to_commit()` restaura desde snapshots** — limpia `self._entities` y reconstruye completamente desde el snapshot del commit, incluyendo entidades creadas dinámicamente.
- **Entity creation va ANTES de entity deltas** — para que los deltas puedan referenciar entidades recién creadas en el mismo turno.
- **`to_core_models()` retorna 5 valores** — `(entity_deltas, entity_creations, world_deltas, dramatic_delta, choices)`. Todos los adapters deben hacer unpacking de 5.
- **`AdvanceNarrativeRequest` defaults a `adapter_type="ollama"`** — los tests deben pasar explícitamente `adapter_type: "mock"`.
- **No acoplar el core a ningún cliente específico** — si una implementación del core requiere importar FastAPI, Flutter, o cualquier framework de UI, es un error de diseño.
- **Las interfaces ABC son el contrato público del motor** — `NarrativeRepository` y `AIAdapter` son lo que un integrador externo implementa para conectar su stack al CNE.
