# Guia: Arquitectura del Proyecto

> Esta guia explica como esta organizado el proyecto Causal Narrative Engine
> (CNE). Esta pensada para alguien que nunca ha trabajado con arquitectura de
> software. Si un concepto te resulta nuevo, no te preocupes: cada seccion lo
> explica desde cero con ejemplos reales del codigo.

---

## 1. Las 4 capas del proyecto

Imagina el proyecto como un edificio de 4 pisos. Cada piso tiene una
responsabilidad clara y no se mete en el trabajo de los otros.

### Piso 1: Core Engine (`cne_core/`)

Es el cerebro del motor. Contiene toda la logica narrativa: validar que la
historia no tenga contradicciones, calcular los medidores dramaticos, y
gestionar el estado de la historia en memoria.

**Caracteristicas clave:**
- No depende de NADA externo (ni base de datos, ni API, ni framework web).
- Es sincrono (no usa `async/await`).
- Solo usa la biblioteca estandar de Python.

```
cne_core/
  models/       --> Los "sustantivos" del sistema
    world.py        WorldDefinition, Entity, EntityType, NarrativeTone
    event.py        NarrativeEvent, CausalEdge, EntityDelta, DramaticDelta
    commit.py       NarrativeCommit, Branch, NarrativeChoice

  engine/       --> Los "verbos" del sistema
    causal_validator.py   Verifica que el grafo de eventos sea un DAG valido
    dramatic_engine.py    Calcula los 7 medidores y detecta eventos forzados
    state_machine.py      Orquesta todo: recibe decisiones, aplica cambios

  interfaces/   --> Los "contratos" (que debe hacer cada pieza externa)
    repository.py     Define QUE operaciones necesita la persistencia
    ai_adapter.py     Define QUE debe hacer un adaptador de IA

  ai/           --> Herramientas para comunicarse con la IA
    context_builder.py     Construye el contexto narrativo para el LLM
    response_schema.py     Define el formato JSON que la IA debe retornar
    response_validator.py  Valida que la respuesta de la IA sea correcta
```

### Piso 2: Persistencia (`persistence/`)

Guarda y recupera datos de PostgreSQL. Implementa el contrato que el Core
define en `NarrativeRepository`.

```
persistence/
  database.py              Configuracion de la conexion a la base de datos
  models/                  Modelos ORM (tablas de la base de datos)
    world_orm.py             WorldORM, EntityORM
    event_orm.py             EventORM, CausalEdgeORM
    commit_orm.py            CommitORM, BranchORM, ChoiceORM
  repositories/
    postgresql_repository.py   La implementacion concreta de NarrativeRepository
  queries/
    causal_queries.py          Consultas SQL recursivas para validacion causal
```

### Piso 3: Adaptadores de IA (`adapters/`)

Conectan el motor con distintos proveedores de IA. Todos implementan el
contrato `AIAdapter` definido en el Core.

```
adapters/
  mock_adapter.py       Respuestas predefinidas, para tests (sin API key)
  anthropic_adapter.py  Conecta con Claude (API de Anthropic)
  ollama_adapter.py     Conecta con LLMs locales gratuitos (gemma3, llama)
```

### Piso 4: API REST (`api/`)

La puerta de entrada HTTP al motor. Usa FastAPI para exponer endpoints y
orquesta las otras capas.

```
api/
  main.py              Crea la app FastAPI y registra los routers
  config.py            Variables de configuracion del servidor
  dependencies.py      Inyeccion de dependencias (conecta todo)
  routers/
    worlds.py            Endpoints para crear/leer/borrar mundos
    narrative.py         Endpoints para avanzar la historia
    health.py            Health check
  services/
    narrative_service_v2.py   El orquestador: conecta engine + repo + adapter
  models/
    requests.py          Esquemas de peticiones HTTP (Pydantic)
    responses.py         Esquemas de respuestas HTTP (Pydantic)
```

---

## 2. La regla de oro de dependencias

Esta es la regla mas importante del proyecto:

> **El Core Engine NUNCA importa de `persistence/`, `adapters/`, ni `api/`.**

Las dependencias van en UNA sola direccion: las capas externas dependen del
Core, nunca al reves.

```
   Importaciones PERMITIDAS              Importaciones PROHIBIDAS
   ========================              ========================

   api/ ---------> cne_core/             cne_core/ -X-> api/
   api/ ---------> persistence/          cne_core/ -X-> persistence/
   api/ ---------> adapters/             cne_core/ -X-> adapters/
   persistence/ -> cne_core/             persistence/ -X-> api/
   adapters/ ----> cne_core/             adapters/ -X-> api/
```

Si lo dibujas como un diagrama, el Core esta en el centro y todo apunta
hacia el:

```
         +-----------+
         |   api/    |
         +-----+-----+
               |
       +-------+--------+
       |                 |
       v                 v
  +-----------+   +-----------+
  |adapters/  |   |persistence|
  +-----------+   +-----------+
       |                 |
       +-------+---------+
               |
               v
        +-----------+
        | cne_core/ |
        +-----------+
```

### Por que importa esto?

Porque el Core puede usarse **sin FastAPI, sin PostgreSQL y sin ningun
adaptador especifico**. Si alguien quiere usar el motor en un juego de
consola, solo necesita `import cne_core` y escribir su propia persistencia
y adaptador de IA. No arrastra dependencias innecesarias.

Puedes verificar esta regla tu mismo: abre cualquier archivo dentro de
`cne_core/` y revisa los `import`. Solo veras imports de otros modulos
dentro de `cne_core/` o de la biblioteca estandar de Python.

---

## 3. Interfaces como contratos (ABC)

Una **interfaz** es un contrato que dice "si quieres participar, debes
ofrecer estos servicios". En Python se implementan con `ABC` (Abstract Base
Class).

> Para entender las ABC en detalle, lee `guia_python.md`.

### Ejemplo real: NarrativeRepository

El archivo `cne_core/interfaces/repository.py` define la interfaz
`NarrativeRepository`. Contiene metodos como:

```python
class NarrativeRepository(ABC):

    @abstractmethod
    async def save_world(self, world: WorldDefinition) -> None: ...

    @abstractmethod
    async def get_world(self, world_id: str) -> WorldDefinition | None: ...

    @abstractmethod
    async def save_commit(self, commit: NarrativeCommit) -> None: ...

    @abstractmethod
    async def get_commit(self, commit_id: str) -> NarrativeCommit | None: ...

    # ... 30 metodos abstractos en total
```

Este contrato dice **QUE** operaciones necesita el sistema, pero no dice
**COMO** implementarlas. El "como" lo decide cada implementacion concreta.

### Ejemplo real: AIAdapter

El archivo `cne_core/interfaces/ai_adapter.py` define:

```python
class AIAdapter(ABC):

    @abstractmethod
    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal: ...

    @abstractmethod
    async def validate_response(self, raw_response: str) -> NarrativeProposal: ...

    @abstractmethod
    def get_model_info(self) -> dict[str, str]: ...
```

Tres adaptadores distintos implementan este contrato:

| Adaptador | Archivo | Para que sirve |
|-----------|---------|----------------|
| `MockAdapter` | `adapters/mock_adapter.py` | Tests automaticos, sin API key |
| `AnthropicAdapter` | `adapters/anthropic_adapter.py` | Produccion con Claude |
| `OllamaAdapter` | `adapters/ollama_adapter.py` | LLMs locales gratuitos |

El Core no sabe (ni le importa) cual se usa. Solo sabe que recibe algo que
cumple el contrato `AIAdapter`.

---

## 4. Patron Repository

El patron Repository separa **"que guardar"** de **"donde guardarlo"**.

Imagina que tienes una biblioteca. El bibliotecario (Core) te dice "guarda
este libro". No le importa si lo pones en una estanteria de madera, en un
archivero de metal, o en una caja. Solo quiere que cuando pida el libro de
vuelta, se lo devuelvas.

En el proyecto funciona asi:

```
  StateMachine                NarrativeRepository              PostgreSQLRepository
  (Core Engine)               (Contrato ABC)                   (Implementacion)
  ============                ================                 ====================

  "Necesito guardar    --->   save_commit(commit)     <---   INSERT INTO commits ...
   este commit"               get_commit(id)          <---   SELECT * FROM commits ...
                              save_event(event)       <---   INSERT INTO events ...
```

La relacion en codigo es:

```
StateMachine  (no conoce la persistencia, trabaja en memoria)
      |
      | usa indirectamente a traves de NarrativeServiceV2
      v
NarrativeRepository (ABC)  <--- contrato definido en cne_core/
      ^
      | implementa
      |
PostgreSQLRepository  (persistence/repositories/postgresql_repository.py)
```

El `StateMachine` es deliberadamente ignorante de la persistencia. Trabaja
100% en memoria. Es `NarrativeServiceV2` (en la capa API) quien conecta el
engine con el repositorio.

**Podrias escribir un `MongoRepository` o un `JSONFileRepository`** que
implemente los mismos 30 metodos, y el Core seguiria funcionando sin cambiar
una linea.

---

## 5. Inyeccion de dependencias

La inyeccion de dependencias es una forma elegante de decir: "no crees tus
propias herramientas, deja que alguien te las pase".

En el proyecto, `api/dependencies.py` es quien "pasa las herramientas":

```python
# api/dependencies.py (simplificado)

async def get_repository() -> AsyncGenerator[NarrativeRepository, None]:
    """Crea un repositorio PostgreSQL con una sesion de base de datos."""
    async with get_session() as session:
        yield PostgreSQLRepository(session)

def get_cache(request: Request) -> CacheBackend:
    """Obtiene el cache de Redis desde el estado de la app."""
    return getattr(request.app.state, "cache", NullCache())

async def get_narrative_service_v2(
    repo: NarrativeRepository = Depends(get_repository),
    cache: CacheBackend = Depends(get_cache),
) -> NarrativeServiceV2:
    """Construye el servicio principal con todas sus dependencias."""
    return NarrativeServiceV2(repository=repo, cache=cache)
```

Cuando un endpoint necesita el servicio, simplemente lo "pide":

```python
# api/routers/worlds.py (simplificado)

@router.post("", response_model=WorldResponse, status_code=201)
async def create_world(
    request: CreateWorldRequest,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    # 'service' ya viene con su repositorio y cache inyectados
    world = WorldDefinition(...)
    await service.save_world(world)
```

El endpoint no sabe como se creo el `NarrativeServiceV2`, ni que base de
datos usa, ni si hay cache o no. Solo lo recibe listo para usar.

### Por que esto facilita los tests?

Porque en los tests puedes reemplazar `get_repository` por una funcion que
retorne un mock en lugar de conectar a PostgreSQL. El endpoint sigue
funcionando igual, pero sin necesitar una base de datos real.

---

## 6. "Donde encuentro X?" -- Referencia rapida

| Quiero... | Archivo |
|-----------|---------|
| Definir un mundo nuevo | `cne_core/models/world.py` |
| Entender los eventos narrativos | `cne_core/models/event.py` |
| Entender commits y ramas | `cne_core/models/commit.py` |
| Validar que el DAG no tenga ciclos | `cne_core/engine/causal_validator.py` |
| Ver como funcionan los 7 medidores | `cne_core/engine/dramatic_engine.py` |
| Ver la maquina de estados en memoria | `cne_core/engine/state_machine.py` |
| Ver el contrato de persistencia | `cne_core/interfaces/repository.py` |
| Ver el contrato de IA | `cne_core/interfaces/ai_adapter.py` |
| Ver como se arma el contexto para la IA | `cne_core/ai/context_builder.py` |
| Ver el formato JSON que retorna la IA | `cne_core/ai/response_schema.py` |
| Guardar/recuperar datos en PostgreSQL | `persistence/repositories/postgresql_repository.py` |
| Ver las tablas de la base de datos | `persistence/models/` |
| Endpoints REST de mundos | `api/routers/worlds.py` |
| Endpoints REST de narrativa | `api/routers/narrative.py` |
| Configuracion del servidor | `api/config.py` |
| Inyeccion de dependencias | `api/dependencies.py` |
| Orquestador principal | `api/services/narrative_service_v2.py` |
| Tests del Core Engine | `tests/test_fase1.py` |
| Tests de adaptadores | `tests/test_adapters.py` |

---

## 7. "Pruebalo tu mismo" -- Traza una peticion

La mejor forma de entender la arquitectura es seguir el recorrido de una
peticion real. Vamos a trazar que pasa cuando alguien hace:

```
POST /worlds
{
  "name": "Mundo Medieval",
  "genre": "fantasy",
  "tone": "dramatic",
  "initial_situation": "Un reino al borde de la guerra civil..."
}
```

### Paso 1: El router recibe la peticion

Archivo: `api/routers/worlds.py`

FastAPI recibe el HTTP POST, valida el JSON contra `CreateWorldRequest`
(Pydantic), e inyecta el servicio via `Depends(get_narrative_service_v2)`.

### Paso 2: La inyeccion de dependencias construye el servicio

Archivo: `api/dependencies.py`

`get_narrative_service_v2()` se ejecuta automaticamente. Internamente:
1. Llama a `get_repository()` que crea un `PostgreSQLRepository` con una
   sesion de base de datos.
2. Llama a `get_cache()` que obtiene el backend de cache.
3. Retorna `NarrativeServiceV2(repository=repo, cache=cache)`.

### Paso 3: El servicio orquesta la operacion

Archivo: `api/services/narrative_service_v2.py`

El router llama a `await service.save_world(world)`. El servicio recibe un
`WorldDefinition` (dataclass del Core) y lo pasa al repositorio.

### Paso 4: El repositorio persiste en la base de datos

Archivo: `persistence/repositories/postgresql_repository.py`

`PostgreSQLRepository.save_world(world)` convierte el dataclass en un modelo
ORM (`WorldORM`) y ejecuta el INSERT en PostgreSQL via SQLAlchemy.

### El camino completo

```
  Cliente HTTP
       |
       v
  api/routers/worlds.py          (recibe y valida la peticion)
       |
       v
  api/dependencies.py            (construye el servicio con sus dependencias)
       |
       v
  api/services/narrative_service_v2.py   (orquesta la logica)
       |
       v
  persistence/repositories/      (convierte a ORM y guarda en PostgreSQL)
  postgresql_repository.py
       |
       v
  PostgreSQL                     (almacena los datos)
```

Intenta hacer este ejercicio con otros endpoints, como
`POST /worlds/{world_id}/start` o `POST /commits/{commit_id}/advance`.
Veras que el patron se repite: router --> servicio --> repositorio. En los
endpoints de narrativa, ademas veras como entra el `AIAdapter` para generar
texto y como el `StateMachine` valida la coherencia antes de persistir.

---

> **Siguiente lectura**: para entender los conceptos de Python usados aqui
> (dataclasses, ABC, async/await, Pydantic), lee `guia_python.md`.
