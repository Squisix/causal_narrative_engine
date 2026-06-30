# Guia de Integracion — Causal Narrative Engine (CNE)

Esta guia explica como conectar tu propio sistema al motor narrativo CNE.

Hay dos formas de integrarse:
1. **SDK Python** — importar `cne_core` directamente en tu codigo Python
2. **API REST** — consumir los endpoints HTTP desde cualquier lenguaje

Y dos interfaces extensibles:
1. **NarrativeRepository** — conectar tu propia base de datos
2. **AIAdapter** — conectar tu propio LLM

---

## Tabla de contenidos

- [Arquitectura](#arquitectura)
- [Uso directo del SDK Python](#uso-directo-del-sdk-python)
- [Uso via API REST](#uso-via-api-rest)
- [Implementar NarrativeRepository](#implementar-narrativerepository)
- [Implementar AIAdapter](#implementar-aiadapter)
- [El Sistema Dramatico (SDMM)](#el-sistema-dramatico-sdmm)
- [Las 4 Propiedades Garantizadas](#las-4-propiedades-garantizadas)

---

## Arquitectura

```
┌────────────────────────────────────────────────┐
│  Tu aplicacion (Flutter, web, CLI, otro)       │
└───────────┬────────────────────────────────────┘
            │ import cne_core  /  HTTP
┌───────────▼────────────────────────────────────┐
│  API REST (FastAPI)  o  SDK Python directo     │
└───────────┬────────────────────────────────────┘
            │
┌───────────▼────────────────────────────────────┐
│  Core Engine                                   │
│  ┌──────────────┐ ┌──────────────────────────┐ │
│  │CausalValidator│ │DramaticEngine (SDMM)    │ │
│  └──────────────┘ └──────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │StateMachine (orquestador)                  │ │
│  └────────────────────────────────────────────┘ │
└──────┬──────────────────────────┬──────────────┘
       │                          │
┌──────▼──────────┐       ┌──────▼──────────┐
│NarrativeRepository│     │AIAdapter         │
│(interfaz ABC)    │      │(interfaz ABC)    │
│                  │      │                  │
│Implementaciones: │      │Implementaciones: │
│- PostgreSQL ✅   │      │- Anthropic ✅    │
│- InMemory ✅     │      │- Ollama ✅       │
│- Tu propia BD    │      │- Mock ✅         │
└─────────────────┘       │- Tu propio LLM   │
                          └─────────────────┘
```

**Principio clave**: la IA propone eventos, el motor valida coherencia causal. La coherencia es propiedad estructural del motor, no del LLM.

---

## Uso directo del SDK Python

El Core Engine no tiene dependencias externas. Solo necesitas Python 3.11+.

```bash
pip install -e .
```

### Ejemplo completo

```python
from cne_core import (
    WorldDefinition, Entity, EntityType, NarrativeTone,
    StateMachine, NarrativeChoice, DramaticDelta,
)

# 1. Definir la semilla del mundo
hero = Entity(
    name="Kael",
    entity_type=EntityType.CHARACTER,
    attributes={"health": 100, "magic": 50}
)

world = WorldDefinition(
    name="Las Tierras Rotas",
    context="Un mundo postapocaliptico donde la magia resurge entre las ruinas.",
    protagonist="Kael, un recolector que descubre poderes latentes",
    era="Post-colapso, 300 anos despues",
    tone=NarrativeTone.MYSTERIOUS,
    initial_entities=[hero],
)

# 2. Crear el motor
engine = StateMachine(world)

# 3. Iniciar la historia
result = engine.start(
    initial_narrative="Kael encuentra un cristal brillante entre los escombros...",
    initial_choices=[
        NarrativeChoice(text="Tocar el cristal"),
        NarrativeChoice(text="Alejarse con cautela"),
        NarrativeChoice(text="Buscar a alguien que sepa que es"),
    ],
    initial_summary="Kael descubre un cristal magico en las ruinas.",
)

print(f"Commit: {result.commit.id[:8]}")
print(f"Drama: tension={result.dramatic_state['tension']}, hope={result.dramatic_state['hope']}")

# 4. Avanzar la historia con una decision
result = engine.advance_story(
    choice_text="Tocar el cristal",
    narrative_text="Al tocar el cristal, una onda de energia recorre su cuerpo...",
    summary="Kael absorbe la energia del cristal y despierta poderes magicos.",
    choices=[
        NarrativeChoice(text="Intentar controlar la magia"),
        NarrativeChoice(text="Huir asustado"),
    ],
    dramatic_delta=DramaticDelta(tension=15, hope=10, mystery=20, chaos=5),
)

print(result.display())

# 5. Consultar el tronco activo (resumen comprimido de la historia)
print(engine.get_trunk_summary())

# 6. Viajar en el tiempo a un commit anterior
old_result = engine.go_to_commit(result.commit.id)
```

### Clases principales del SDK

| Clase | Modulo | Descripcion |
|-------|--------|-------------|
| `WorldDefinition` | `cne_core.models.world` | Semilla inmutable del mundo |
| `Entity` | `cne_core.models.world` | Personaje, objeto o locacion |
| `StateMachine` | `cne_core.engine.state_machine` | Orquestador del motor |
| `StoryAdvanceResult` | `cne_core.engine.state_machine` | Resultado de cada transicion |
| `NarrativeCommit` | `cne_core.models.commit` | Un punto en el arbol de decisiones |
| `NarrativeChoice` | `cne_core.models.commit` | Opcion disponible para el jugador |
| `DramaticDelta` | `cne_core.models.event` | Cambios al vector dramatico |
| `DramaticVector` | `cne_core.engine.dramatic_engine` | Los 7 medidores |
| `CausalValidator` | `cne_core.engine.causal_validator` | Garantiza que el grafo es un DAG |

Todo se importa desde `cne_core` directamente:

```python
from cne_core import WorldDefinition, StateMachine, NarrativeChoice
```

---

## Uso via API REST

### Levantar el servidor

```bash
# Instalar dependencias
pip install -e ".[api,persistence]"

# Levantar PostgreSQL
docker-compose up -d

# Crear tablas
alembic upgrade head

# Iniciar servidor
uvicorn api.main:app --reload --port 8000
```

Documentacion interactiva: `http://localhost:8000/docs`

### Endpoints

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/worlds` | Crear un mundo (semilla) |
| `GET` | `/worlds/{world_id}` | Obtener un mundo |
| `DELETE` | `/worlds/{world_id}` | Eliminar un mundo |
| `POST` | `/worlds/{world_id}/start` | Iniciar narrativa -> primer commit |
| `POST` | `/commits/{commit_id}/advance` | Tomar decision -> nuevo commit |
| `GET` | `/commits/{commit_id}` | Obtener un commit |
| `GET` | `/commits/{commit_id}/dramatic` | Vector dramatico de un commit |
| `GET` | `/health` | Estado del servidor |

### Flujo completo con curl

```bash
# 1. Crear un mundo
curl -X POST http://localhost:8000/worlds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reino de Valdris",
    "context": "Un reino medieval al borde de la guerra. El rey ha muerto.",
    "protagonist": "Lyra, la princesa heredera",
    "era": "Medieval fantastico",
    "tone": "dark",
    "antagonist": "Malachar, el consejero corrupto",
    "max_depth": 20
  }'

# Respuesta: { "world_id": "abc-123-...", ... }

# 2. Iniciar la narrativa
curl -X POST http://localhost:8000/worlds/abc-123-.../start \
  -H "Content-Type: application/json" \
  -d '{
    "adapter_type": "mock"
  }'

# Respuesta: { "commit_id": "def-456-...", "narrative_text": "...", "choices": [...], ... }

# 3. Avanzar con una decision
curl -X POST http://localhost:8000/commits/def-456-.../advance \
  -H "Content-Type: application/json" \
  -d '{
    "choice": "Confrontar a Malachar directamente"
  }'

# 4. Consultar estado dramatico
curl http://localhost:8000/commits/def-456-.../dramatic
```

### Flujo con Python requests

```python
import requests

BASE = "http://localhost:8000"

# Crear mundo
world = requests.post(f"{BASE}/worlds", json={
    "name": "Mi Mundo",
    "context": "Un universo de ciencia ficcion...",
    "protagonist": "Zara",
    "era": "Ano 3045",
    "tone": "mysterious",
}).json()

# Iniciar narrativa
commit = requests.post(
    f"{BASE}/worlds/{world['world_id']}/start",
    json={"adapter_type": "mock"}
).json()

print(commit["narrative_text"])
print("Opciones:", [c["text"] for c in commit["choices"]])

# Avanzar
next_commit = requests.post(
    f"{BASE}/commits/{commit['commit_id']}/advance",
    json={"choice": commit["choices"][0]["text"]}
).json()
```

---

## Implementar NarrativeRepository

Si quieres usar tu propia base de datos (MongoDB, SQLite, Redis, etc.), implementa la interfaz `NarrativeRepository`.

**Archivo de referencia**: `cne_core/interfaces/repository.py`
**Implementacion completa**: `persistence/repositories/postgresql_repository.py`

### La interfaz

```python
from cne_core.interfaces.repository import NarrativeRepository

class MiRepository(NarrativeRepository):
    """Tu implementacion con tu BD."""

    # --- Metodos requeridos (todos async) ---

    # WorldDefinition
    async def save_world(self, world: WorldDefinition) -> None: ...
    async def get_world(self, world_id: str) -> WorldDefinition | None: ...
    async def list_worlds(self, limit: int = 50) -> list[WorldDefinition]: ...

    # NarrativeCommit
    async def save_commit(self, commit: NarrativeCommit) -> None: ...
    async def get_commit(self, commit_id: str) -> NarrativeCommit | None: ...
    async def get_trunk(self, commit_id: str, max_depth: int = 100) -> list[NarrativeCommit]: ...
    async def get_children_commits(self, commit_id: str) -> list[NarrativeCommit]: ...
    async def get_latest_commit_id(self, world_id: str) -> str | None: ...

    # NarrativeEvent
    async def save_event(self, event: NarrativeEvent) -> None: ...
    async def get_event(self, event_id: str) -> NarrativeEvent | None: ...
    async def get_events_for_commit(self, commit_id: str) -> list[NarrativeEvent]: ...

    # Choices
    async def save_choices(self, commit_id: str, choices: list[NarrativeChoice]) -> None: ...
    async def get_choices(self, commit_id: str) -> list[NarrativeChoice]: ...

    # Grafo causal
    async def save_causal_edge(self, edge: CausalEdge) -> None: ...
    async def check_causal_path_exists(self, from_id: str, to_id: str) -> bool: ...
    async def get_causal_parents(self, event_id: str) -> list[str]: ...
    async def get_causal_children(self, event_id: str) -> list[str]: ...

    # Estado dramatico
    async def save_dramatic_state(self, commit_id, vector, forced_event=None, trigger_meter=None) -> None: ...
    async def get_dramatic_state(self, commit_id: str) -> dict[str, int] | None: ...
    async def get_forced_event_type(self, commit_id: str) -> str | None: ...
    async def save_dramatic_delta(self, event_id, meter, delta, reason=None) -> None: ...

    # Entidades
    async def get_entity_state(self, entity_id: str, at_commit: str) -> dict | None: ...
    async def save_entity_snapshot(self, commit_id: str, entity_states: dict) -> None: ...

    # Ramas
    async def save_branch(self, branch: Branch) -> None: ...
    async def get_branch(self, branch_id: str) -> Branch | None: ...
    async def list_branches(self, world_id: str) -> list[Branch]: ...

    # Stats
    async def count_commits(self, world_id: str) -> int: ...
    async def count_all_commits(self) -> int: ...
    async def count_worlds(self) -> int: ...
    async def count_events(self) -> int: ...

    # State snapshots
    async def get_nearest_snapshot(self, commit_id: str) -> tuple[str, dict] | None: ...
    async def get_deltas_since(self, from_id: str, to_id: str) -> list[tuple[str, Any]]: ...
```

### Ejemplo: implementacion minima con SQLite

```python
import sqlite3
import json
from cne_core.interfaces.repository import NarrativeRepository
from cne_core.models.world import WorldDefinition
from cne_core.models.commit import NarrativeCommit, NarrativeChoice, Branch

class SQLiteRepository(NarrativeRepository):
    def __init__(self, db_path: str = "cne.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS worlds (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS commits (
                id TEXT PRIMARY KEY,
                world_id TEXT NOT NULL,
                parent_id TEXT,
                depth INTEGER NOT NULL,
                data TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    async def save_world(self, world: WorldDefinition) -> None:
        conn = sqlite3.connect(self.db_path)
        # Serializar el dataclass a JSON
        data = json.dumps({
            "id": world.id, "name": world.name,
            "context": world.context, "protagonist": world.protagonist,
            "era": world.era, "tone": world.tone.value,
            # ... resto de campos
        })
        conn.execute(
            "INSERT OR REPLACE INTO worlds (id, data) VALUES (?, ?)",
            (world.id, data)
        )
        conn.commit()
        conn.close()

    async def get_world(self, world_id: str) -> WorldDefinition | None:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT data FROM worlds WHERE id = ?", (world_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        data = json.loads(row[0])
        return WorldDefinition(**data)  # Reconstruir desde JSON

    # ... implementar el resto de metodos ...
```

### Metodos criticos a implementar primero

Para que el motor funcione, estos son los metodos minimos:

1. `save_world` / `get_world` — persistir la semilla
2. `save_commit` / `get_commit` / `get_trunk` — el arbol de decisiones
3. `save_choices` / `get_choices` — las opciones por commit
4. `save_dramatic_state` / `get_dramatic_state` — vector dramatico
5. `save_branch` / `list_branches` — metadata de ramas

Los metodos de grafo causal (`save_causal_edge`, `check_causal_path_exists`) son importantes para la propiedad P1 (garantizar DAG sin ciclos) pero el `CausalValidator` del core ya hace esta verificacion en memoria.

---

## Implementar AIAdapter

Si quieres conectar tu propio LLM (OpenAI, Mistral, etc.), implementa la interfaz `AIAdapter`.

**Archivo de referencia**: `cne_core/interfaces/ai_adapter.py`
**Implementacion mock**: `adapters/mock_adapter.py`
**Implementacion Anthropic**: `adapters/anthropic_adapter.py`
**Implementacion Ollama**: `adapters/ollama_adapter.py`

### La interfaz

```python
from cne_core.interfaces.ai_adapter import (
    AIAdapter, NarrativeContext, NarrativeProposal
)

class MiAdapter(AIAdapter):
    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
        """Genera la proxima narrativa dado el contexto del mundo."""
        ...

    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        """Parsea y valida la respuesta cruda del LLM."""
        ...

    def get_model_info(self) -> dict[str, str]:
        """Retorna info del modelo: provider, model, version."""
        ...
```

### NarrativeContext — lo que recibe tu adapter

El motor construye un `NarrativeContext` con todo lo necesario:

```python
@dataclass
class NarrativeContext:
    world_definition: WorldDefinition    # La semilla completa del mundo
    current_depth: int                   # Profundidad narrativa actual
    current_dramatic_state: dict[str, int]  # Los 7 medidores
    current_entity_states: dict[str, Any]   # Estado de personajes/objetos
    current_world_vars: dict[str, Any]      # Variables globales
    commit_chain: list[NarrativeCommit]     # Historia hasta ahora
    player_choice: str | None               # Que eligio el jugador
    forced_constraint: ForcedEventConstraint | None  # Si hay evento forzado
```

### NarrativeProposal — lo que tu adapter debe retornar

```python
@dataclass
class NarrativeProposal:
    narrative_text: str              # Texto narrativo (150-250 palabras)
    summary: str                     # Resumen de 1 oracion para el tronco
    choices: list[NarrativeChoice]   # 2-4 opciones para el jugador

    # Efectos (opcionales pero recomendados)
    entity_deltas: list[EntityDelta] = []       # Cambios en personajes
    world_deltas: list[WorldVariableDelta] = []  # Cambios en variables globales
    dramatic_delta: DramaticDelta | None = None  # Cambios al vector dramatico

    # Metadata
    causal_reason: str | None = None     # Por que ocurre este evento
    is_ending: bool = False              # Es el final de la historia?
    forced_event_type: str | None = None # Si fue forzado por umbral
```

### Contrato JSON que el LLM debe retornar

Si tu LLM retorna JSON, este es el schema esperado:

```json
{
  "narrative": "Texto inmersivo de 150-250 palabras...",
  "summary": "Resumen causal de 1 oracion para el tronco",
  "choices": ["opcion A", "opcion B", "opcion C"],
  "choice_dramatic_preview": [
    {"choice": "opcion A", "tension_delta": 15, "hope_delta": -10, "tone": "confrontacional"},
    {"choice": "opcion B", "tension_delta": -5, "hope_delta": 5, "tone": "diplomatico"}
  ],
  "entity_deltas": [
    {"entity_id": "uuid", "attribute": "health", "old_value": 100, "new_value": 85}
  ],
  "world_deltas": [
    {"variable": "political_stability", "old_value": 60, "new_value": 48}
  ],
  "dramatic_deltas": {
    "tension": 15, "hope": -8, "chaos": 5,
    "rhythm": 0, "saturation": 8, "connection": -3, "mystery": 10
  },
  "causal_reason": "Por que este evento ocurre dado el estado actual",
  "forced_event_type": null,
  "is_ending": false
}
```

### Ejemplo: adapter con OpenAI

```python
import json
from openai import AsyncOpenAI
from cne_core.interfaces.ai_adapter import (
    AIAdapter, NarrativeContext, NarrativeProposal, AIGenerationError
)
from cne_core.models.commit import NarrativeChoice
from cne_core.models.event import DramaticDelta

class OpenAIAdapter(AIAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
        # Construir prompt desde el contexto
        system_prompt = self._build_system_prompt(context)
        user_prompt = self._build_user_prompt(context)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        return await self.validate_response(raw)

    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            raise AIGenerationError("LLM retorno JSON invalido")

        choices = [
            NarrativeChoice(text=c) for c in data.get("choices", [])
        ]

        dramatic = data.get("dramatic_deltas", {})
        delta = DramaticDelta(
            tension=dramatic.get("tension", 0),
            hope=dramatic.get("hope", 0),
            chaos=dramatic.get("chaos", 0),
            rhythm=dramatic.get("rhythm", 0),
            saturation=dramatic.get("saturation", 0),
            connection=dramatic.get("connection", 0),
            mystery=dramatic.get("mystery", 0),
        )

        return NarrativeProposal(
            narrative_text=data["narrative"],
            summary=data["summary"],
            choices=choices,
            dramatic_delta=delta,
            causal_reason=data.get("causal_reason"),
            is_ending=data.get("is_ending", False),
        )

    def get_model_info(self) -> dict[str, str]:
        return {
            "provider": "openai",
            "model": self.model,
            "version": "1.0",
        }

    def _build_system_prompt(self, context: NarrativeContext) -> str:
        world = context.world_definition
        return f"""Eres un narrador para el mundo "{world.name}".
Contexto: {world.context}
Protagonista: {world.protagonist}
Tono: {world.tone.value}

DEBES retornar JSON con este schema exacto:
{{
  "narrative": "texto de 150-250 palabras",
  "summary": "resumen de 1 oracion",
  "choices": ["opcion 1", "opcion 2", "opcion 3"],
  "dramatic_deltas": {{"tension": 0, "hope": 0, "chaos": 0, ...}},
  "causal_reason": "por que ocurre esto",
  "is_ending": false
}}"""

    def _build_user_prompt(self, context: NarrativeContext) -> str:
        if context.player_choice:
            return f"El jugador eligio: {context.player_choice}"
        return "Genera el inicio de la historia."
```

### Usar OllamaAdapter (LLMs locales gratuitos)

El motor incluye un adapter listo para usar con [Ollama](https://ollama.com), que ejecuta LLMs localmente sin API keys ni costos.

#### Instalacion

```bash
# 1. Instalar Ollama: https://ollama.com
# 2. Descargar un modelo
ollama pull gemma3:4b
```

Modelos recomendados:

| Modelo | RAM | Calidad | Velocidad |
|--------|-----|---------|-----------|
| `gemma3:4b` | ~3GB | Buena | Rapido |
| `qwen3:4b` | ~3GB | Buena | Rapido |
| `llama3.2:3b` | ~2GB | Aceptable | Muy rapido |
| `mistral:7b` | ~4GB | Muy buena | Requiere GPU |

#### Uso directo (SDK Python)

```python
import asyncio
from adapters.ollama_adapter import OllamaAdapter
from cne_core import WorldDefinition, NarrativeTone, Entity, EntityType
from cne_core.interfaces.ai_adapter import NarrativeContext

async def main():
    adapter = OllamaAdapter(model="gemma3:4b")

    hero = Entity(name="Kael", entity_type=EntityType.CHARACTER,
                  attributes={"health": 100, "magic": 50})
    world = WorldDefinition(
        name="Las Tierras Rotas",
        context="Un mundo postapocaliptico donde la magia resurge.",
        protagonist="Kael, un recolector con poderes latentes",
        era="Post-colapso", tone=NarrativeTone.MYSTERIOUS,
        initial_entities=[hero],
    )

    ctx = NarrativeContext(
        world_definition=world, current_depth=0,
        current_dramatic_state={
            "tension": 30, "hope": 60, "chaos": 20, "rhythm": 50,
            "saturation": 0, "connection": 40, "mystery": 50
        },
        current_entity_states={}, current_world_vars={}, commit_chain=[],
    )

    result = await adapter.generate_narrative(ctx)
    print(result.narrative_text)
    print("Opciones:", [c.text for c in result.choices])

asyncio.run(main())
```

#### Uso via API REST

```bash
# Iniciar narrativa con Ollama
curl -X POST http://localhost:8000/worlds/{world_id}/start \
  -H "Content-Type: application/json" \
  -d '{"adapter_type": "ollama"}'

# Con modelo personalizado
curl -X POST http://localhost:8000/worlds/{world_id}/start \
  -H "Content-Type: application/json" \
  -d '{
    "adapter_type": "ollama",
    "adapter_config": {
      "model": "mistral:7b",
      "temperature": 0.8
    }
  }'
```

#### Configuracion

En `.env`:
```
OLLAMA_MODEL=gemma3:4b
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEMPERATURE=0.7
```

### Constraint de evento forzado

Cuando el SDMM detecta que un umbral se cruzo (ej: `tension > 85`), el motor pasa un `forced_constraint` en el contexto. Tu adapter DEBE respetar este constraint:

```python
async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
    if context.forced_constraint:
        # El motor exige un tipo de evento especifico
        event_type = context.forced_constraint.event_type.value  # ej: "CLIMAX"
        trigger = context.forced_constraint.trigger_meter         # ej: "tension"
        constraint_text = context.forced_constraint.constraint_text
        # Incluir en el prompt: "DEBE ocurrir un CLIMAX..."
```

---

## El Sistema Dramatico (SDMM)

El motor mantiene un vector de 7 dimensiones que evoluciona con cada evento:

| Medidor | Rango | Inicio | Que mide |
|---------|-------|--------|----------|
| `tension` | 0-100 | 30 | Conflicto activo |
| `hope` | 0-100 | 60 | Cosas pueden mejorar |
| `chaos` | 0-100 | 20 | Entropia del mundo |
| `rhythm` | 0-100 | 50 | Velocidad narrativa |
| `saturation` | 0-100 | 0 | Agotamiento del arco |
| `connection` | 0-100 | 40 | Vinculo emocional |
| `mystery` | 0-100 | 50 | Preguntas sin resolver |

### Interacciones automaticas

El motor aplica estas reglas automaticamente despues de cada delta:

```
tension > 50     ->  hope -= ((tension - 50) // 10) * 2
chaos > 60       ->  rhythm += (chaos - 60) // 10
saturation > 70  ->  connection -= (saturation - 70) // 5
hope < 20        ->  mystery += 3
```

### Umbrales -> Eventos forzados

Cuando un medidor cruza un umbral, el motor fuerza un tipo de evento:

```
# Combinaciones (prioridad 1)
mystery > 65 AND tension > 65  ->  CLIMAX_REVELATION
connection > 70 AND tension > 60  ->  EMOTIONAL_MOMENT

# Individuales (prioridad 2)
saturation > 95  ->  ARC_CLOSURE
tension > 85     ->  CLIMAX
hope < 10        ->  TRAGEDY
chaos > 80       ->  CHAOS_STORM
saturation > 85  ->  PLOT_TWIST
tension < 15     ->  DISRUPTIVE
hope > 90        ->  UNEXPECTED_THREAT
```

El evento forzado no interrumpe la historia — se integra causalmente al DAG como consecuencia de los eventos que elevaron el medidor.

---

## Las 4 Propiedades Garantizadas

El motor garantiza estas propiedades estructuralmente, independientemente del LLM:

### P1 — Causalidad
El grafo de eventos es siempre un DAG (Directed Acyclic Graph). No hay ciclos. Antes de insertar una arista A->B, el motor verifica que no exista B->...->A.

### P2 — Determinismo
El estado `S(t)` es reconstruible desde snapshots + deltas. Dado un commit cualquiera, se puede reconstruir el estado exacto del mundo en ese punto.

### P3 — Versionado
Cada decision crea un commit con `parent_id` (arbol tipo Git). Se puede navegar hacia atras con `go_to_commit()` y crear ramas alternativas.

### P4 — Consistencia
Entidades muertas no actuan. Variables globales se mantienen en rango valido. Los deltas propuestos por la IA se validan antes de aplicar.

---

## Configuracion de Docker

El `docker-compose.yml` incluido levanta:
- **PostgreSQL 16** en puerto `5433` (para no colisionar con instalaciones locales)
- **Adminer** en puerto `8080` (UI web para la BD)

```bash
docker-compose up -d
alembic upgrade head
```

Variables de entorno para la conexion:
```
DATABASE_URL=postgresql+asyncpg://cne_user:cne_password_dev@localhost:5433/cne_db
```

---

## Estructura de la base de datos

| Tabla | Descripcion |
|-------|-------------|
| `worlds` | WorldDefinition (semilla del mundo) |
| `entities` | Personajes, objetos, locaciones |
| `branches` | Metadata de ramas narrativas |
| `commits` | Arbol de decisiones (tipo Git) |
| `events` | Eventos narrativos (unidad atomica) |
| `event_edges` | DAG causal (sin ciclos) |
| `entity_deltas` | Cambios en atributos de entidades |
| `world_variable_deltas` | Cambios en variables globales |
| `dramatic_states` | Vector de 7 medidores por commit |
| `dramatic_deltas` | Historial de cambios dramaticos |
| `choices` | Opciones disponibles por commit |
