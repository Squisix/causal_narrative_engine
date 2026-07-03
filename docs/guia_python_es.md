# Guia: Python Avanzado en CNE

Esta guia explica las funcionalidades avanzadas de Python que se usan en el
Causal Narrative Engine (CNE). Si sabes escribir funciones, clases basicas y
usar listas/diccionarios, esta guia te llevara al siguiente nivel con ejemplos
reales del proyecto.

---

## 1. Dataclasses (`@dataclass`)

Cuando creas una clase normal en Python, tienes que escribir manualmente el
`__init__`, el `__repr__` y el `__eq__`. Una **dataclass** genera todo eso
automaticamente a partir de los campos que declares. Piensa en ella como una
clase que existe para guardar datos de forma estructurada.

En el CNE, **todos los modelos de dominio** son dataclasses. Asi se define una
entidad del mundo narrativo en `cne_core/models/world.py`:

```python
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class Entity:
    name:        str
    entity_type: EntityType
    attributes:  dict[str, Any]       = field(default_factory=dict)
    id:          str                  = field(default_factory=lambda: str(uuid.uuid4()))
    created_at_depth:    int          = 0
    destroyed_at_depth:  int | None   = None
```

Python genera automaticamente un `__init__` equivalente a:

```python
def __init__(self, name, entity_type, attributes=None, id=None, ...):
    self.name = name
    self.entity_type = entity_type
    self.attributes = attributes if attributes is not None else {}
    self.id = id if id is not None else str(uuid.uuid4())
    ...
```

### Por que `field(default_factory=...)` y no `= []` o `= {}`

Este es un error clasico en Python. Si escribieras `attributes: dict = {}`,
**todas las instancias compartirian el mismo diccionario**. Observa:

```python
# MAL -- no hagas esto
@dataclass
class Malo:
    items: list = []     # Todas las instancias comparten esta MISMA lista

a = Malo()
b = Malo()
a.items.append("hola")
print(b.items)  # ['hola'] -- b tambien tiene "hola"!
```

```python
# BIEN -- cada instancia recibe su propia lista
@dataclass
class Bueno:
    items: list = field(default_factory=list)

a = Bueno()
b = Bueno()
a.items.append("hola")
print(b.items)  # [] -- b tiene su propia lista vacia
```

En el CNE veras `field(default_factory=dict)` para diccionarios,
`field(default_factory=list)` para listas, y lambdas para valores calculados
como UUIDs: `field(default_factory=lambda: str(uuid.uuid4()))`.

Un ejemplo mas complejo es la configuracion dramatica en `WorldDefinition`
(`cne_core/models/world.py`), que usa un lambda para generar un diccionario
con valores por defecto:

```python
dramatic_config: dict[str, int] = field(default_factory=lambda: {
    "tension":    30,
    "hope":       60,
    "chaos":      20,
    "rhythm":     50,
    "saturation": 0,
    "connection": 40,
    "mystery":    50,
})
```

---

## 2. Enums (`str + Enum`)

Un **Enum** es un tipo que solo puede tomar un conjunto fijo de valores. En
lugar de usar strings sueltas como `"character"` o `"faction"` (que puedes
escribir mal sin que Python se queje), un Enum te da autocompletado y
validacion.

En el CNE se usa el patron `str + Enum`, que significa que el enum hereda de
`str` ademas de `Enum`. Esto hace que sus valores sean **directamente
serializables a JSON**, sin necesidad de conversion manual.

De `cne_core/models/world.py`:

```python
from enum import Enum

class EntityType(str, Enum):
    CHARACTER = "character"
    FACTION   = "faction"
    ARTIFACT  = "artifact"
    LOCATION  = "location"
```

La ventaja practica de `str + Enum`:

```python
# Sin str + Enum, necesitarias .value para serializar:
import json
json.dumps({"type": EntityType.CHARACTER.value})  # funciona

# Con str + Enum, funciona directamente:
json.dumps({"type": EntityType.CHARACTER})  # tambien funciona!
```

Otro ejemplo del proyecto son los tipos de eventos en
`cne_core/models/event.py`:

```python
class EventType(str, Enum):
    DECISION    = "decision"
    CONSEQUENCE = "consequence"
    FORCED      = "forced"
    CLIMAX      = "climax"
    REVELATION  = "revelation"
    ENDING      = "ending"
```

Y los tipos de evento forzado en `cne_core/engine/dramatic_engine.py`:

```python
class ForcedEventType(str, Enum):
    CLIMAX              = "CLIMAX"
    TRAGEDY             = "TRAGEDY"
    PLOT_TWIST          = "PLOT_TWIST"
    CHAOS_STORM         = "CHAOS_STORM"
    CLIMAX_REVELATION   = "CLIMAX_REVELATION"
    # ... y mas
```

---

## 3. Abstract Base Classes (ABC)

Una **Abstract Base Class** es una clase que define un contrato: dice que
metodos deben existir, pero no los implementa. Cualquier clase que herede de
ella **esta obligada a implementar todos** los metodos abstractos, o Python
lanzara un error al intentar crear una instancia.

En el CNE, las ABCs son el mecanismo central de extensibilidad. El core del
motor **nunca sabe** si esta hablando con PostgreSQL, SQLite, MongoDB, o un
diccionario en memoria. Solo conoce la interfaz.

De `cne_core/interfaces/repository.py`:

```python
from abc import ABC, abstractmethod

class NarrativeRepository(ABC):

    @abstractmethod
    async def save_world(self, world: WorldDefinition) -> None:
        """Persiste una WorldDefinition (la semilla)."""
        pass

    @abstractmethod
    async def get_world(self, world_id: str) -> WorldDefinition | None:
        """Recupera una WorldDefinition por ID."""
        pass

    @abstractmethod
    async def save_commit(self, commit: NarrativeCommit) -> None:
        pass

    # ... 20+ metodos mas
```

`PostgreSQLRepository` en `persistence/repositories/postgresql_repository.py`
implementa esta interfaz:

```python
class PostgreSQLRepository(NarrativeRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_world(self, world: WorldDefinition) -> None:
        world_orm = WorldORM(
            id=world.id,
            name=world.name,
            # ... convierte dataclass a ORM
        )
        # ... usa SQLAlchemy para persistir
```

Lo mismo ocurre con la IA. De `cne_core/interfaces/ai_adapter.py`:

```python
class AIAdapter(ABC):

    @abstractmethod
    async def generate_narrative(
        self,
        context: NarrativeContext
    ) -> NarrativeProposal:
        """Genera la proxima narrativa dado el contexto actual."""
        pass

    @abstractmethod
    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, str]:
        pass
```

El directorio `adapters/` tiene tres implementaciones: `AnthropicAdapter`
(Claude), `OllamaAdapter` (LLMs locales) y `MockAdapter` (tests). Todas
cumplen el mismo contrato.

Si quieres ver como las ABCs permiten intercambiar implementaciones sin
modificar el core, lee `guia_arquitectura.md`.

---

## 4. Type Hints

Los **type hints** son anotaciones que indican que tipo de dato espera o
retorna cada variable, parametro o funcion. Python no los aplica en tiempo
de ejecucion (puedes pasar un `int` donde dice `str` y no explotara), pero
son invaluables para autocompletado del IDE, documentacion, y deteccion
temprana de errores con herramientas como `mypy`.

Estos son los patrones mas comunes en el CNE:

```python
# Tipo basico
name: str
depth: int = 0

# Union: puede ser str o None
parent_id: str | None = None            # Python 3.10+
destroyed_at_depth: int | None = None

# Diccionario con tipos para clave y valor
attributes: dict[str, Any]              # claves string, valores de cualquier tipo
dramatic_state: dict[str, int]          # claves string, valores enteros

# Lista tipada
constraints: list[str]                  # lista de strings
caused_by: list[str] = field(default_factory=list)

# Tipo de retorno
def is_root(self) -> bool:              # retorna un booleano
    return len(self.caused_by) == 0

async def get_world(self, world_id: str) -> WorldDefinition | None:
    # retorna un WorldDefinition o None si no existe
    ...

# Tupla con tipos especificos
async def get_nearest_snapshot(self, commit_id: str) -> tuple[str, dict[str, Any]] | None:
    # retorna (snapshot_commit_id, entity_states) o None
    ...
```

El tipo `Any` (de `typing`) significa "cualquier tipo". Se usa cuando el valor
puede ser un string, un numero, un booleano, o incluso otro diccionario. En
el CNE, `attributes: dict[str, Any]` permite que una entidad tenga atributos
como `{"health": 100, "alive": True, "location": "bosque"}`.

---

## 5. Properties (`@property`)

Una **property** es un metodo que se accede como si fuera un atributo. En
lugar de llamar `entity.is_alive()` con parentesis, escribes
`entity.is_alive` directamente. Se usa cuando el valor se calcula a partir de
otros atributos y quieres que el acceso sea limpio.

De `cne_core/models/world.py`:

```python
@dataclass
class Entity:
    destroyed_at_depth: int | None = None

    @property
    def is_alive(self) -> bool:
        return self.destroyed_at_depth is None
```

Uso:

```python
hero = Entity(name="Kael", entity_type=EntityType.CHARACTER)
print(hero.is_alive)        # True (no se usa parentesis)

hero.destroyed_at_depth = 5
print(hero.is_alive)        # False
```

Otro ejemplo de `cne_core/models/event.py`, donde `EntityDelta` usa una
property para generar un resumen legible:

```python
@dataclass
class EntityDelta:
    entity_name: str
    attribute:   str
    old_value:   Any
    new_value:   Any

    @property
    def delta_summary(self) -> str:
        return f"{self.entity_name}.{self.attribute}: {self.old_value} -> {self.new_value}"
```

```python
delta = EntityDelta(
    entity_id="abc", entity_name="Kael",
    attribute="health", old_value=100, new_value=85
)
print(delta.delta_summary)  # "Kael.health: 100 -> 85"
```

---

## 6. Async / Await

Cuando tu programa hace una consulta a una base de datos o una llamada HTTP,
pasan milisegundos (o segundos) esperando una respuesta. Con codigo
**sincrono**, el programa se bloquea y no hace nada hasta que llega la
respuesta. Con `async/await`, Python puede atender otras peticiones mientras
espera.

En el CNE, la division es clara:
- **Core Engine** (`cne_core/engine/`): sincrono. Opera sobre datos en
  memoria, no hay I/O.
- **Persistencia** (`persistence/`): asincrono. Cada query a PostgreSQL es
  una operacion de I/O.
- **API** (`api/`): asincrona. FastAPI maneja multiples peticiones HTTP
  concurrentes.

De `cne_core/interfaces/repository.py`:

```python
class NarrativeRepository(ABC):

    @abstractmethod
    async def save_world(self, world: WorldDefinition) -> None:
        pass

    @abstractmethod
    async def get_world(self, world_id: str) -> WorldDefinition | None:
        pass
```

Al implementarlo en `PostgreSQLRepository`:

```python
async def save_world(self, world: WorldDefinition) -> None:
    world_orm = WorldORM(id=world.id, name=world.name, ...)
    self.session.add(world_orm)
    await self.session.flush()   # <-- aqui Python puede atender otra cosa
```

Otros patrones async que veras en el proyecto:

```python
# async with: para recursos que se abren y cierran (sesiones de DB)
async with async_session() as session:
    repo = PostgreSQLRepository(session)
    await repo.save_world(world)
    await session.commit()

# async for: para iterar sobre resultados de queries grandes
async for row in result:
    commits.append(row_to_commit(row))
```

La regla de oro: si una funcion usa `await` internamente, debe ser declarada
con `async def`. Y solo puedes usar `await` dentro de funciones `async`.

---

## 7. Pruebalo tu mismo

Abre una terminal de Python (`python` o `python3`) y prueba estos ejemplos
directamente.

### Crear una Entity con dataclass

```python
from dataclasses import dataclass, field
from enum import Enum
import uuid

class EntityType(str, Enum):
    CHARACTER = "character"
    ARTIFACT  = "artifact"

@dataclass
class Entity:
    name: str
    entity_type: EntityType
    attributes: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    destroyed_at_depth: int | None = None

    @property
    def is_alive(self) -> bool:
        return self.destroyed_at_depth is None

# Crea dos entidades
hero = Entity(name="Kael", entity_type=EntityType.CHARACTER, attributes={"health": 100})
sword = Entity(name="Excalibur", entity_type=EntityType.ARTIFACT, attributes={"damage": 50})

print(hero)              # Entity(name='Kael', ...)
print(hero.is_alive)     # True
print(hero.id)           # un UUID unico
print(sword.attributes)  # {'damage': 50}

# Mata al heroe
hero.destroyed_at_depth = 3
print(hero.is_alive)     # False
```

### Verificar que `field(default_factory=...)` funciona

```python
a = Entity(name="A", entity_type=EntityType.CHARACTER)
b = Entity(name="B", entity_type=EntityType.CHARACTER)

a.attributes["stealth"] = 90
print(b.attributes)  # {} -- cada instancia tiene su propio dict
```

### Crear un Enum y serializar a JSON

```python
import json

print(EntityType.CHARACTER)            # EntityType.CHARACTER
print(EntityType.CHARACTER.value)      # "character"
print(json.dumps({"type": EntityType.CHARACTER}))  # {"type": "character"}
```

### Ejecutar los tests reales del proyecto

El archivo `tests/test_fase1.py` contiene ejemplos ejecutables de todos estos
conceptos aplicados al motor narrativo completo. No requiere base de datos ni
API keys:

```bash
python tests/test_fase1.py
```

Para ver los tests de los adapters de IA (usando `MockAdapter`):

```bash
pytest tests/test_adapters.py -v
```

---

## Resumen rapido

| Concepto | Para que sirve | Donde se usa en CNE |
|----------|----------------|---------------------|
| `@dataclass` | Generar `__init__`, `__repr__`, `__eq__` automaticamente | Todos los modelos (`Entity`, `NarrativeEvent`, `NarrativeCommit`) |
| `field(default_factory=...)` | Defaults mutables seguros (listas, dicts) | Listas de deltas, diccionarios de atributos, UUIDs |
| `str + Enum` | Enums serializables a JSON | `EntityType`, `EventType`, `ForcedEventType`, `NarrativeTone` |
| `ABC + @abstractmethod` | Interfaces que obligan a implementar metodos | `NarrativeRepository`, `AIAdapter` |
| Type hints | Documentacion, autocompletado, deteccion de errores | Todo el proyecto |
| `@property` | Metodos que parecen atributos | `Entity.is_alive`, `EntityDelta.delta_summary` |
| `async/await` | I/O no bloqueante (DB, HTTP, IA) | Persistencia, API, AI Adapters |
