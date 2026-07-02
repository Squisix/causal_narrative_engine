# Causal Narrative Engine (CNE) — Arbol Literario

> Lee esto antes de tocar cualquier archivo de codigo.
> Skills disponibles en `.agents/skills/` para referencia detallada.

---

## Que es este proyecto

Un **motor narrativo independiente** basado en causalidad formal para generar
historias ramificadas con IA manteniendo coherencia verificable. El motor es
un framework reutilizable que cualquier proyecto puede integrar — un juego,
una herramienta de escritura, una API, o un pipeline de generacion de contenido.

**El motor es el producto.** Los clientes son responsabilidad del integrador.

Objetivos:
1. **Motor independiente**: `pip install cne-core` y funciona. Sin acoplamientos.
2. **Extensible por diseno**: interfaces abstractas (ABC) para persistencia y IA.
3. **Paper academico**: publicar en AIIDE / IEEE CoG.

---

## Modelo Formal

```
CNE = (W, E, S, D, T, C, Phi)
```

| Simbolo | Nombre | Descripcion |
|---------|--------|-------------|
| `W` | WorldDefinition | Semilla inmutable: genero, tono, reglas, restricciones |
| `E` | Event Space | Todos los eventos narrativos posibles |
| `S(t)` | Narrative State | `(Entities(t), EntityCreations(t), WorldVars(t), D(t), History(t))` |
| `D(t)` | Dramatic Vector | `(tension, hope, chaos, rhythm, saturation, connection, mystery) in [0,100]^7` |
| `T` | Transition Function | `S(t+1) = T(S(t), choice, proposal_IA)` |
| `C` | Causal Graph | DAG dirigido de eventos. Sin ciclos. |
| `Phi` | Dramatic Function | Evalua umbrales de D(t) -> ForcedEventConstraint | None |

**4 propiedades garantizadas:**
- **P1 Causalidad**: el grafo de eventos es siempre un DAG (sin ciclos)
- **P2 Determinismo**: `S(t)` es reconstruible desde snapshots + deltas
- **P3 Versionado**: cada decision = commit con parent_id (arbol Git-like)
- **P4 Consistencia**: entidades muertas no actuan, variables en rango valido

---

## Arquitectura

```
+------------------------------------------------------+
|              Cualquier cliente externo               |
|   (juego, API, CLI, herramienta de escritura, etc.)  |
+---------------------+--------------------------------+
                      | import cne_core  /  HTTP  /  SDK
+---------------------v--------------------------------+
|            FastAPI REST  [COMPLETADO]                |
|    api/ — NarrativeServiceV2 + routers              |
+---------------------+--------------------------------+
                      |
+---------------------v--------------------------------+
|           Core Engine  —  cne_core/                  |
|   CausalValidator  |  DramaticEngine  |  StateMachine|
|   ContextBuilder   |  ResponseSchema  |  Interfaces  |
+----------+------------------------------+-----------+
           |                              |
+----------v----------+      +-----------v------------+
|  Persistence Layer  |      |      AI Adapter          |
|                     |      |                          |
|  Interface ABC      |      |  Interface ABC           |
|  PostgreSQL [OK]    |      |  Anthropic [OK]          |
|                     |      |  Ollama [OK]             |
|                     |      |  Mock [OK]               |
+---------------------+      +--------------------------+
```

**Principio clave**: la coherencia es propiedad estructural del motor, NO del LLM.
La IA propone. El motor valida y decide.

---

## Estado del Proyecto

| Fase | Estado | Descripcion |
|------|--------|-------------|
| Fase 1 | COMPLETADA | Core Engine en memoria (sin dependencias) |
| Fase 2 | COMPLETADA | Persistencia PostgreSQL + SQLAlchemy async |
| Fase 3 | COMPLETADA | AI Adapter (Anthropic + Ollama + Mock) |
| Fase 4 | COMPLETADA | FastAPI REST API |
| Fase 5 | Pendiente | Release publico en PyPI |
| Fase 6 | Pendiente | Paper academico |

---

## Estructura del Proyecto

```
cne_core/                          # Core Engine
├── models/
│   ├── world.py                   # WorldDefinition, Entity, EntityType, NarrativeTone
│   ├── event.py                   # NarrativeEvent, CausalEdge, EntityDelta, EntityCreation,
│   │                              # WorldVariableDelta, DramaticDelta
│   └── commit.py                  # NarrativeCommit, Branch, NarrativeChoice
├── engine/
│   ├── causal_validator.py        # CausalValidator: deteccion de ciclos DAG (BFS)
│   ├── dramatic_engine.py         # DramaticEngine: SDMM completo con Phi
│   └── state_machine.py           # StateMachine: orquestador en memoria
├── interfaces/
│   ├── repository.py              # NarrativeRepository ABC
│   └── ai_adapter.py              # AIAdapter ABC + NarrativeContext/NarrativeProposal
└── ai/
    ├── context_builder.py         # ContextBuilder: tronco activo para LLMs
    ├── response_schema.py         # NarrativeResponse (Pydantic) + to_core_models()
    └── response_validator.py      # Validacion del JSON de la IA

adapters/                          # Implementaciones de AIAdapter
├── mock_adapter.py                # MockAdapter: determinista, para tests
├── anthropic_adapter.py           # AnthropicAdapter: Claude API
└── ollama_adapter.py              # OllamaAdapter: LLMs locales gratuitos

persistence/                       # Persistencia PostgreSQL
├── database.py                    # DatabaseConfig, async session factory
├── models/
│   ├── world_orm.py               # WorldORM, EntityORM
│   ├── event_orm.py               # EventORM, EntityDeltaORM, EntityCreationORM
│   └── commit_orm.py              # CommitORM, BranchORM, ChoiceORM, DramaticStateORM
├── repositories/
│   └── postgresql_repository.py   # PostgreSQLRepository
└── queries/
    └── causal_queries.py          # CTE recursiva para validacion causal en SQL

api/                               # FastAPI REST API
├── main.py                        # App FastAPI con routers
├── config.py                      # Configuracion del servidor
├── dependencies.py                # Inyeccion de dependencias
├── routers/
│   ├── worlds.py                  # CRUD de mundos
│   ├── narrative.py               # start, advance, goto, commits
│   └── health.py                  # Health check
├── services/
│   └── narrative_service_v2.py    # Orquestador con persistencia
└── models/
    ├── requests.py                # Pydantic request schemas
    └── responses.py               # Pydantic response schemas

cli/                               # CLI interactivo
migrations/                        # Alembic (4 migraciones)
tests/                             # Tests
web/                               # Interfaz web (en desarrollo)
```

---

## Contrato JSON de la IA

La IA debe retornar este JSON (validado por ResponseValidator):

```json
{
  "narrative": "Texto inmersivo 150-250 palabras",
  "summary": "Resumen causal de 1 oracion para el tronco",
  "choices": ["opcion A", "opcion B", "opcion C"],
  "choice_dramatic_preview": [
    { "choice": "opcion A", "tension_delta": 15, "hope_delta": -10, "tone": "confrontacional" }
  ],
  "entity_deltas": [{"entity_id": "uuid", "attribute": "health", "old_value": 100, "new_value": 85}],
  "entity_creations": [
    {"entity_name": "Nombre", "entity_type": "character|artifact|faction|location",
     "attributes": {"health": 100, "possessed_by": null, "location": "lugar", "usable": true, "effect": "desc"}}
  ],
  "world_deltas": [{"variable": "political_stability", "old_value": 60, "new_value": 48}],
  "dramatic_deltas": {
    "tension": 15, "hope": -8, "chaos": 5,
    "rhythm": 0, "saturation": 8, "connection": -3, "mystery": 10
  },
  "causal_reason": "Por que este evento ocurre dado el estado actual",
  "forced_event_type": null,
  "is_ending": false
}
```

`to_core_models()` retorna **5-tuple**:
```python
entity_deltas, entity_creations, world_deltas, dramatic_delta, choices = response.to_core_models()
```

---

## API REST Endpoints

```
POST   /worlds                       # Crear WorldDefinition
GET    /worlds/{world_id}            # Obtener mundo
DELETE /worlds/{world_id}            # Eliminar mundo
POST   /worlds/{world_id}/start      # Iniciar historia
GET    /worlds/{world_id}/commits    # Listar commits
POST   /commits/{commit_id}/advance  # Tomar decision
GET    /commits/{commit_id}          # Estado de un commit
GET    /commits/{commit_id}/dramatic # Vector dramatico
POST   /commits/{commit_id}/goto     # Navegar a commit anterior
GET    /health                       # Estado del servidor
```

---

## Convenciones de Codigo

### Nombrado
- **Clases**: PascalCase (`NarrativeCommit`, `DramaticEngine`)
- **Metodos/variables**: snake_case (`advance_story`, `current_commit_id`)
- **Constantes/enums**: UPPER_SNAKE o PascalCase para Enum
- **IDs**: siempre `str` (UUID serializable)

### Patrones
- **Dataclasses** para modelos de dominio (`@dataclass`)
- **`str` + `Enum`** para enums (serializables a JSON)
- **`field(default_factory=...)`** para defaults mutables
- **`ABC`** para interfaces (Repository, AIAdapter) — no implementar en Core
- **Async** en persistence/api — el Core Engine es sincrono

### Errores
```python
class CausalCycleError(Exception): ...
class EventNotFoundError(Exception): ...
class ValidationError(Exception): ...
```

---

## Implementaciones Incluidas

| Componente | Implementacion | Cuando usar |
|------------|---------------|-------------|
| Repository | `PostgreSQLRepository` | Produccion y tests de integracion |
| AIAdapter | `MockAdapter` | Tests sin API key (determinista) |
| AIAdapter | `AnthropicAdapter` | Produccion con Claude |
| AIAdapter | `OllamaAdapter` | LLMs locales gratuitos (gemma3, llama, etc.) |

---

## Comandos Utiles

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

## Notas Criticas

- **No usar `vitality`** — fue reemplazado por `DramaticVector`.
- **`StateMachine` es sincrono** — la capa async vive en `NarrativeServiceV2`.
- **El Core Engine nunca importa de `persistence/`** — la dependencia va en direccion opuesta.
- **La IA nunca modifica directamente el estado** — siempre propone, el motor valida.
- **`go_to_commit()` restaura desde snapshots** — limpia `self._entities` y reconstruye completamente.
- **Entity creation va ANTES de entity deltas** — para que los deltas referencien entidades nuevas.
- **`to_core_models()` retorna 5 valores** — todos los adapters hacen unpacking de 5.
- **`AdvanceNarrativeRequest` defaults a `adapter_type="ollama"`** — los tests deben pasar `adapter_type: "mock"`.
- **No acoplar el core a ningun cliente** — si requiere importar FastAPI o Flutter, es un error.
