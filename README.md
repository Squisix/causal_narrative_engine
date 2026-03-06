# Causal Narrative Engine (CNE)

**Motor narrativo independiente basado en causalidad formal para generar historias ramificadas con IA manteniendo coherencia verificable.**

---

## ¿Qué es CNE?

Un framework reutilizable que cualquier proyecto puede integrar — un juego, una herramienta de escritura, una API, o un pipeline de generación de contenido.

**La coherencia es propiedad estructural del motor, NO del LLM.**

```
┌──────────────────────────────────┐
│  IA propone eventos              │
│         ↓                        │
│  Motor valida coherencia causal  │
│         ↓                        │
│  Motor decide qué pasa           │
└──────────────────────────────────┘
```

---

## Estado actual

| Fase | Estado | Descripción |
|------|--------|-------------|
| **Fase 1** | ✅ **COMPLETADA** | Core Engine en memoria (sin dependencias) |
| **Fase 2** | ✅ **COMPLETADA** | Persistencia con PostgreSQL + SQLAlchemy async |
| **Fase 3** | 🔲 Pendiente | AI Adapter (Anthropic/Claude) |
| **Fase 4** | 🔲 Pendiente | FastAPI REST + SDK Python |
| **Fase 5** | 🔲 Pendiente | Release público + docs |

---

## Quickstart — 5 minutos

```bash
# 1. Instalar dependencias
pip install -e ".[persistence,dev]"

# 2. Levantar PostgreSQL
docker-compose up -d

# 3. Crear tablas
alembic upgrade head

# 4. Ejecutar ejemplo
python examples/fase2_example.py

# 5. Ejecutar tests
pytest tests/test_fase2.py -v
```

**Ver:** [QUICKSTART_FASE2.md](QUICKSTART_FASE2.md) para instrucciones detalladas.

---

## Conceptos Core

### 1️⃣ Modelo Formal

```
CNE = (W, E, S, D, T, C, Φ)
```

- **W** = WorldDefinition (semilla inmutable)
- **E** = Espacio de eventos narrativos
- **S(t)** = Estado del mundo en tiempo t
- **D(t)** = Vector Dramático de 7 medidores
- **T** = Función de transición (IA propone → motor valida)
- **C** = Grafo causal (DAG sin ciclos)
- **Φ** = Evaluador dramático (umbrales → eventos forzados)

**4 garantías:**
- ✅ **Causalidad**: El grafo es siempre un DAG válido
- ✅ **Determinismo**: El estado es reconstruible desde snapshots
- ✅ **Versionado**: Tipo Git, puedes volver atrás en decisiones
- ✅ **Consistencia**: Entidades muertas no actúan, variables en rango

### 2️⃣ Sistema Dramático Multi-Medidor (SDMM)

7 medidores independientes en vez de un solo indicador:

| Medidor | Qué mide |
|---------|----------|
| `tension` | Nivel de conflicto activo |
| `hope` | Percepción de que las cosas pueden mejorar |
| `chaos` | Entropía del mundo |
| `rhythm` | Velocidad narrativa |
| `saturation` | Agotamiento del arco actual |
| `connection` | Vínculo emocional con personajes |
| `mystery` | Preguntas sin resolver |

**Umbrales → Eventos Forzados:**
```
tension > 85        →  CLIMAX forzado
hope < 10           →  TRAGEDIA forzada
saturation > 95     →  CIERRE DE ARCO forzado
mystery + tension > 130  →  REVELACIÓN CLIMÁTICA
```

### 3️⃣ Arquitectura Independiente

```
┌────────────────────────────────┐
│  Cualquier cliente externo     │
│  (juego, web, CLI...)          │
└───────────┬────────────────────┘
            │ import cne_core
┌───────────▼────────────────────┐
│     Core Engine                │
│  CausalValidator │ DramaticEngine
│  StateMachine    │ NarrativeRunner
└────┬──────────────────┬────────┘
     │                  │
┌────▼─────────┐  ┌────▼─────────┐
│ Persistence  │  │ AI Adapter   │
│              │  │              │
│ Interface    │  │ Interface    │
│ ─────────    │  │ ─────────    │
│ PostgreSQL ✅│  │ Anthropic 🔲 │
│ SQLite       │  │ OpenAI       │
│ InMemory ✅  │  │ Mock ✅      │
└──────────────┘  └──────────────┘
```

---

## Instalación

### Fase 1: Core Engine (sin dependencias)

```bash
pip install -e .
```

**Solo Python 3.11+ stdlib** — tests sin PostgreSQL, sin API keys, sin Docker.

### Fase 2: Con PostgreSQL

```bash
pip install -e ".[persistence,dev]"
docker-compose up -d
alembic upgrade head
```

### Fase 3+: Con IA

```bash
pip install -e ".[ai,persistence,dev]"
export ANTHROPIC_API_KEY="sk-..."
```

---

## Tests

```bash
# Fase 1: Core Engine en memoria
python tests/test_fase1.py

# Fase 2: Persistencia (requiere Docker)
pytest tests/test_fase2.py -v

# Todos los tests con coverage
pytest --cov=cne_core --cov=persistence --cov-report=term-missing
```

---

## Estructura del proyecto

```
cne_core/                          # ✅ Fase 1
├── models/                        # Dataclasses (WorldDefinition, NarrativeEvent, etc.)
├── engine/                        # CausalValidator, DramaticEngine, StateMachine
└── interfaces/                    # ✅ Fase 2 - Contratos abstractos

persistence/                       # ✅ Fase 2
├── database.py                    # Config SQLAlchemy 2.0 async
├── models/                        # ORM models (WorldORM, EventORM, etc.)
├── repositories/                  # PostgreSQLRepository
├── queries/                       # CTEs recursivas (validación causal en SQL)
└── state_rebuilder.py             # Reconstrucción de estado desde deltas

migrations/                        # ✅ Fase 2
└── versions/
    └── 001_initial_schema.py      # Schema completo (10 tablas)

tests/
├── test_fase1.py                  # ✅ Tests Core Engine
└── test_fase2.py                  # ✅ Tests Persistencia

examples/
└── fase2_example.py               # ✅ Ejemplo completo

docker-compose.yml                 # ✅ PostgreSQL + Adminer + Redis
alembic.ini                        # ✅ Migraciones
pyproject.toml                     # ✅ Dependencias por fase
```

---

## Uso programático

### Ejemplo básico (Fase 1 — en memoria)

```python
from cne_core import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core import StateMachine, NarrativeChoice, DramaticDelta

# 1. Crear mundo
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

# 2. Iniciar motor
engine = StateMachine(world)

# 3. Comenzar historia
result = engine.start(
    initial_narrative="El reino está en peligro...",
    initial_choices=[
        NarrativeChoice(text="Ir al palacio"),
        NarrativeChoice(text="Huir a las montañas"),
    ]
)

# 4. Avanzar historia
result = engine.advance_story(
    choice_text="Ir al palacio",
    narrative_text="Aldric cabalga hacia la capital...",
    summary="Aldric acepta la misión.",
    choices=[...],
    dramatic_delta=DramaticDelta(tension=10, hope=-5)
)

print(result.display())
```

### Ejemplo con PostgreSQL (Fase 2)

```python
import asyncio
from persistence.database import DatabaseConfig
from persistence.repositories.postgresql_repository import PostgreSQLRepository

async def main():
    # Configurar DB
    db_config = DatabaseConfig(
        "postgresql+asyncpg://cne_user:cne_password_dev@localhost:5432/cne_db"
    )
    repo = PostgreSQLRepository(db_config)

    # Guardar mundo
    await repo.save_world(world)

    # Guardar commits
    await repo.save_commit(commit)

    # Recuperar historia
    trunk = await repo.get_trunk(commit.id)

asyncio.run(main())
```

---

## Documentación

- **[CLAUDE.md](CLAUDE.md)** — Documentación completa del proyecto (punto de entrada)
- **[QUICKSTART_FASE2.md](QUICKSTART_FASE2.md)** — Instalación rápida en 5 minutos
- **[FASE2_README.md](FASE2_README.md)** — Guía detallada de Fase 2
- **[examples/fase2_example.py](examples/fase2_example.py)** — Ejemplo funcional completo

---

## Tablas de la base de datos

| Tabla | Descripción |
|-------|-------------|
| `worlds` | WorldDefinition (semilla del mundo) |
| `entities` | Personajes, objetos, locaciones |
| `branches` | Metadata de ramas narrativas |
| `commits` | Árbol de decisiones (tipo Git) |
| `events` | Eventos narrativos (unidad atómica) |
| `event_edges` | **DAG causal** (sin ciclos) |
| `entity_deltas` | Cambios en atributos de entidades |
| `world_variable_deltas` | Cambios en variables globales |
| `dramatic_states` | Vector de 7 medidores por commit |
| `dramatic_deltas` | Historial de cambios dramáticos |

**Índices críticos:**
- `event_edges(cause_event_id, effect_event_id)` — Unique
- `commits(parent_id)` — Navegación de ramas
- `events(topo_order)` — Orden causal

---

## Contribuciones Académicas (para el paper)

1. **Literary Tree Model** — Formalización matemática del Árbol Literario
2. **Dramatic Vector Formalism (DVF)** — Vector de 7 dimensiones como elemento formal del estado
3. **Threshold-Driven Narrative Control** — Eventos forzados por umbrales integrados causalmente
4. **Active Trunk Compression** — Compresión de contexto para LLMs preservando coherencia
5. **Coherence as Structural Property** — La coherencia es del motor, no del LLM
6. **Narrative Git Versioning** — Versionado tipo Git de decisiones con reconstrucción determinista

---

## Roadmap

### ✅ Fase 1 — Core Engine
- [x] Dataclasses del dominio
- [x] CausalValidator (DAG sin ciclos)
- [x] DramaticEngine (SDMM)
- [x] StateMachine (orquestador en memoria)
- [x] Tests completos

### ✅ Fase 2 — Persistencia
- [x] Interfaces abstractas (Repository pattern)
- [x] ORM models (SQLAlchemy 2.0 async)
- [x] PostgreSQLRepository
- [x] CTEs recursivas (validación causal en SQL)
- [x] StateRebuilder (estructura base)
- [x] Migraciones (Alembic)
- [x] Docker Compose
- [x] Tests async

### 🔲 Fase 3 — AI Adapter
- [ ] AnthropicAdapter (Claude)
- [ ] MockAIAdapter (tests sin API key)
- [ ] ContextBuilder (tronco activo)
- [ ] ResponseValidator (validar JSON)
- [ ] Integración completa

### 🔲 Fase 4 — API REST
- [ ] FastAPI endpoints
- [ ] SDK Python
- [ ] Documentación OpenAPI
- [ ] Auth & rate limiting

### 🔲 Fase 5 — Release
- [ ] PyPI release
- [ ] Docker image público
- [ ] Docs completas (Sphinx)
- [ ] Ejemplos copy-paste

### 🔲 Fase 6 — Paper
- [ ] Draft inicial
- [ ] Experimentos
- [ ] Métricas formales
- [ ] Submit a AIIDE / IEEE CoG

---

## Licencia

MIT — Ver [LICENSE](LICENSE) para detalles.

---

## Contacto

**¿Problemas?** Abre un issue en GitHub.

**¿Contribuir?** Lee [CONTRIBUTING.md](CONTRIBUTING.md).

**Paper:** TBD (Fase 6)

---

**Hecho con ❤️ para la comunidad de narrativa interactiva.**
