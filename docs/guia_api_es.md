# Guia: API REST -- FastAPI y Pydantic

> Esta guia explica como funciona la API REST del Causal Narrative Engine (CNE).
> Si nunca has trabajado con APIs web, este documento te lleva paso a paso
> desde los conceptos basicos hasta ejemplos funcionales con `curl`.

---

## 1. Que es una API REST

Una **API REST** es una interfaz que permite a cualquier programa comunicarse
con un servidor usando HTTP -- el mismo protocolo que usa tu navegador.

**Conceptos clave:**

- **Recursos**: cada URL representa algo. `/worlds` son mundos, `/commits` son commits narrativos.
- **Metodos HTTP**: definen la accion sobre el recurso.
  - `GET` -- obtener datos (leer un mundo, ver un commit)
  - `POST` -- crear o ejecutar algo (crear mundo, avanzar historia)
  - `DELETE` -- eliminar (borrar un mundo)
- **JSON**: el formato de datos que viaja entre cliente y servidor.
- **Codigos de estado**: el servidor responde con un numero que indica el resultado (200 = OK, 201 = creado, 404 = no encontrado, etc.)

**Por que el CNE tiene una API?** Porque separa el motor narrativo de quien
lo consume. Un juego web, una app movil, un CLI, o un script de Python pueden
usar el mismo motor a traves de HTTP. El motor es el producto; el cliente es
responsabilidad del integrador.

---

## 2. FastAPI

[FastAPI](https://fastapi.tiangolo.com/) es el framework de Python que usa el
CNE para exponer su motor como API REST.

**Caracteristicas principales:**

- **Async por defecto** -- maneja multiples requests concurrentemente.
- **Validacion automatica** -- usa Pydantic para validar datos de entrada.
- **Documentacion interactiva** -- genera Swagger UI en `/docs` y ReDoc en `/redoc` sin escribir una sola linea extra.

Asi se configura en el CNE (`api/main.py`):

```python
from fastapi import FastAPI
from api.routers import health, worlds, narrative

app = FastAPI(
    title="Causal Narrative Engine API",
    description="Motor narrativo basado en causalidad formal...",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Registrar grupos de endpoints
app.include_router(health.router)
app.include_router(worlds.router)
app.include_router(narrative.router)
```

Con estas lineas, FastAPI sabe que existen tres grupos de endpoints y genera
la documentacion automaticamente.

---

## 3. Routers -- organizacion de endpoints

Un **router** agrupa endpoints relacionados bajo un mismo prefijo. En lugar de
tener un archivo gigante con todos los endpoints, cada tema tiene su propio modulo.

**Estructura real del CNE:**

| Archivo | Prefijo | Que maneja |
|---------|---------|------------|
| `api/routers/worlds.py` | `/worlds` | CRUD de mundos (crear, leer, eliminar) |
| `api/routers/narrative.py` | (sin prefijo) | Flujo narrativo (start, advance, goto) |
| `api/routers/health.py` | (sin prefijo) | Health check y estadisticas |

Asi se define un router con prefijo (`api/routers/worlds.py`):

```python
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter(
    prefix="/worlds",
    tags=["worlds"]
)
```

- `prefix="/worlds"` -- todos los endpoints de este router empiezan con `/worlds`.
- `tags=["worlds"]` -- aparecen agrupados en la documentacion Swagger.

Y asi se define un endpoint dentro de ese router:

```python
@router.post("", response_model=WorldResponse, status_code=201)
async def create_world(
    request: CreateWorldRequest,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """Crea un nuevo mundo (semilla) para iniciar historias."""
    # ... logica de creacion ...
```

- `@router.post("")` -- responde a `POST /worlds` (el prefijo se suma al `""`).
- `response_model=WorldResponse` -- dice que forma tiene la respuesta (seccion 5).
- `status_code=201` -- retorna 201 (Created) en vez del 200 por defecto.
- `request: CreateWorldRequest` -- FastAPI valida el body automaticamente (seccion 4).

---

## 4. Pydantic -- validacion automatica

[Pydantic](https://docs.pydantic.dev/) es la libreria que valida los datos
de entrada (requests) y salida (responses). Se definen clases que heredan de
`BaseModel`, y FastAPI las usa automaticamente.

**Request real del CNE** (`api/models/requests.py`):

```python
from pydantic import BaseModel, Field
from typing import Optional

class CreateWorldRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=200, description="Nombre del mundo")
    context: str = Field(..., min_length=10, max_length=2000, description="Descripcion del universo")
    protagonist: str = Field(..., min_length=2, max_length=200, description="Nombre del protagonista")
    era: str = Field(..., min_length=2, max_length=200, description="Epoca o ambientacion")
    tone: str = Field(..., description="Tono: epic, dark, mysterious, adventurous, philosophical, black_humor")

    antagonist: Optional[str] = Field(default="desconocido", max_length=500)
    rules: Optional[str] = Field(default="El mundo sigue sus propias leyes", max_length=1000)
    constraints: list[str] = Field(default_factory=list)
    max_depth: int = Field(default=0, ge=0, description="Maximo decisiones antes de forzar final")
```

**Como leer esto:**

| Sintaxis | Significado |
|----------|-------------|
| `Field(...)` | Campo **obligatorio** (el `...` es el marcador de Pydantic) |
| `Field(default="valor")` | Campo **opcional** con valor por defecto |
| `min_length=3` | El string debe tener al menos 3 caracteres |
| `max_length=200` | El string no puede exceder 200 caracteres |
| `ge=0` | Greater or Equal: el numero debe ser >= 0 |
| `Optional[str]` | Puede ser `str` o `None` |

**Si la validacion falla**, FastAPI retorna automaticamente un error 422 con detalles:

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "String should have at least 3 characters",
      "type": "string_too_short"
    }
  ]
}
```

No necesitas escribir ninguna logica de validacion manual -- Pydantic lo hace por ti.

Otro request importante es `AdvanceNarrativeRequest`:

```python
class AdvanceNarrativeRequest(BaseModel):
    choice: str = Field(..., min_length=1, max_length=500, description="Texto de la opcion elegida")
    custom: bool = Field(default=False, description="True si es opcion escrita por el jugador")
    adapter_type: str = Field(default="mock", description="'mock', 'anthropic' o 'ollama'")
    adapter_config: Optional[dict] = Field(default=None)
```

> **Importante**: `adapter_type` tiene como default `"mock"`. Para producción
> u obtención de respuestas generadas por un LLM local, puedes pasar `"adapter_type": "ollama"`.

---

## 5. Response Models -- forma de la respuesta

El parametro `response_model` en un endpoint le dice a FastAPI que estructura
tiene la respuesta JSON. Pydantic serializa los objetos Python automaticamente.

**Response real del CNE** (`api/models/responses.py`):

```python
class WorldResponse(BaseModel):
    world_id: str
    name: str
    context: str
    protagonist: str
    era: str
    tone: str
    antagonist: str
    rules: str
    constraints: list[str]
    max_depth: int
    created_at: datetime
    total_commits: int = 0
    active_branches: int = 0
```

Cuando el endpoint retorna un objeto `WorldResponse`, FastAPI lo convierte
a JSON con exactamente esos campos. El cliente siempre recibe una estructura
predecible.

La respuesta de un commit narrativo es mas rica:

```python
class NarrativeCommitResponse(BaseModel):
    commit_id: str
    parent_id: Optional[str] = None
    depth: int
    narrative_text: str
    summary: str
    choices: list[ChoiceResponse]
    dramatic_state: DramaticStateResponse
    causal_reason: Optional[str] = None
    is_ending: bool = False
    forced_event_type: Optional[str] = None
    created_at: datetime
```

Cada `ChoiceResponse` tiene texto, un preview dramatico, y un hint de tono:

```python
class ChoiceResponse(BaseModel):
    text: str
    tone_hint: Optional[str] = None
```

---

## 6. Dependency Injection con Depends()

FastAPI tiene un sistema de **inyeccion de dependencias** que resuelve
automaticamente lo que cada endpoint necesita.

**Ejemplo real** (`api/dependencies.py`):

```python
from fastapi import Depends

async def get_repository() -> AsyncGenerator[NarrativeRepository, None]:
    """Crea una sesion de DB y la cierra al terminar la request."""
    async for session in get_session():
        repo = PostgreSQLRepository(session)
        yield repo

async def get_narrative_service_v2(
    repo: NarrativeRepository = Depends(get_repository),
    cache: CacheBackend = Depends(get_cache),
) -> NarrativeServiceV2:
    """Usa el Repository inyectado y el cache."""
    return NarrativeServiceV2(repository=repo, cache=cache)
```

**La cadena funciona asi:**

1. El endpoint declara `service: NarrativeServiceV2 = Depends(get_narrative_service_v2)`
2. FastAPI ve que `get_narrative_service_v2` necesita un `repo` y un `cache`
3. FastAPI llama a `get_repository()` (que abre una sesion de PostgreSQL) y a `get_cache()`
4. Con esos resultados, crea el `NarrativeServiceV2` y se lo pasa al endpoint
5. Al terminar la request, cierra la sesion de DB automaticamente

No necesitas crear manualmente la cadena de dependencias en cada endpoint.
Escribes `Depends(...)` y FastAPI se encarga.

> Para entender la arquitectura de capas completa (engine, repository, adapter),
> lee `guia_arquitectura.md`.

---

## 7. Manejo de errores

Cuando algo sale mal, el endpoint lanza una `HTTPException`:

```python
from fastapi import HTTPException

# Si el mundo no existe
if not world:
    raise HTTPException(
        status_code=404,
        detail=f"World not found: {world_id}"
    )

# Si el tono es invalido
raise HTTPException(
    status_code=400,
    detail="Invalid tone: xyz. Valid values: epic, dark, mysterious, adventurous, philosophical, black_humor"
)
```

**Codigos de error comunes en el CNE:**

| Codigo | Significado | Ejemplo |
|--------|-------------|---------|
| 400 | Bad Request | Tono narrativo invalido |
| 404 | Not Found | Mundo o commit no existe |
| 422 | Validation Error | Pydantic rechazo el JSON (campo faltante, tipo incorrecto) |
| 500 | Internal Server Error | Error inesperado del servidor |

---

## 8. Tabla de endpoints

| Metodo | Path | Que hace | Request Body | Response |
|--------|------|----------|--------------|----------|
| `POST` | `/worlds` | Crear mundo | `CreateWorldRequest` | `WorldResponse` |
| `GET` | `/worlds` | Listar mundos | -- | `list[WorldResponse]` |
| `GET` | `/worlds/{world_id}` | Obtener mundo | -- | `WorldResponse` |
| `DELETE` | `/worlds/{world_id}` | Eliminar mundo | -- | 204 No Content |
| `POST` | `/worlds/{world_id}/start` | Iniciar historia | `StartNarrativeRequest` | `NarrativeCommitResponse` |
| `GET` | `/worlds/{world_id}/commits` | Listar commits | -- | `list[CommitSummaryResponse]` |
| `GET` | `/worlds/{world_id}/latest` | Ultimo commit | -- | `NarrativeCommitResponse` |
| `POST` | `/commits/{commit_id}/advance` | Avanzar historia | `AdvanceNarrativeRequest` | `NarrativeCommitResponse` |
| `GET` | `/commits/{commit_id}` | Estado de commit | -- | `NarrativeCommitResponse` |
| `GET` | `/commits/{commit_id}/dramatic` | Vector dramatico | -- | `DramaticStateResponse` |
| `POST` | `/commits/{commit_id}/goto` | Navegar a commit | -- | `NarrativeCommitResponse` |
| `GET` | `/health` | Health check | -- | `HealthResponse` |
| `GET` | `/stats` | Estadisticas | -- | `StatsResponse` |

---

## 9. Ejemplos con curl

Flujo completo para probar la API desde la terminal.

**Prerequisito**: el servidor debe estar corriendo (ver seccion 10).

### Crear un mundo

```bash
curl -X POST http://localhost:8000/worlds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reino de Valdris",
    "context": "Un reino medieval al borde de la guerra. El rey ha muerto misteriosamente.",
    "protagonist": "Lyra, la princesa heredera",
    "era": "Medieval fantastico, anno 843",
    "tone": "dark",
    "antagonist": "Malachar, el consejero corrupto",
    "rules": "La magia existe pero tiene un precio en sangre",
    "constraints": ["No puede haber viajes en el tiempo", "Los muertos no resucitan"],
    "max_depth": 20
  }'
```

La respuesta incluye un `world_id` -- guardalo para los siguientes pasos.

### Iniciar la historia

```bash
curl -X POST http://localhost:8000/worlds/{world_id}/start \
  -H "Content-Type: application/json" \
  -d '{
    "adapter_type": "mock"
  }'
```

Reemplaza `{world_id}` con el ID real. La respuesta incluye la primera
narrativa, opciones disponibles, y un `commit_id`.

### Avanzar la historia

```bash
curl -X POST http://localhost:8000/commits/{commit_id}/advance \
  -H "Content-Type: application/json" \
  -d '{
    "choice": "Confrontar a Malachar directamente",
    "adapter_type": "mock"
  }'
```

> **Importante**: El default es `"mock"`, por lo que es seguro para testing sin dependencias de IA externas.
> Si deseas usar un modelo local con Ollama, debes pasar explícitamente `"adapter_type": "ollama"`.

### Ver el vector dramatico

```bash
curl http://localhost:8000/commits/{commit_id}/dramatic
```

Retorna los 7 medidores del SDMM (tension, hope, chaos, rhythm, saturation,
connection, mystery).

### Listar commits de un mundo

```bash
curl http://localhost:8000/worlds/{world_id}/commits
```

### Navegar a un commit anterior

```bash
curl -X POST http://localhost:8000/commits/{commit_id}/goto
```

Restaura el estado del engine al punto de ese commit -- util para explorar
ramas alternativas.

### Health check

```bash
curl http://localhost:8000/health
```

---

## 10. Pruebalo tu mismo

### Levantar el servidor

```bash
# Opcion 1: directamente (requiere PostgreSQL corriendo)
uvicorn api.main:app --reload --port 8000

# Opcion 2: con Docker (levanta PostgreSQL automaticamente)
docker-compose up -d
alembic upgrade head
uvicorn api.main:app --reload --port 8000
```

> Para la configuracion completa con Docker, lee `guia_docker.md`.

### Documentacion interactiva

Con el servidor corriendo, abre en tu navegador:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) -- interfaz interactiva donde puedes probar cada endpoint directamente desde el navegador.
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc) -- documentacion mas limpia para leer.

Desde Swagger UI puedes crear un mundo, iniciar una historia, y avanzarla
sin escribir una sola linea de codigo -- todo desde el navegador.

### Flujo minimo de prueba

1. Abre `http://localhost:8000/docs`
2. Busca `POST /worlds` y haz click en "Try it out"
3. Pega el JSON del ejemplo de la seccion 9 y ejecuta
4. Copia el `world_id` de la respuesta
5. Busca `POST /worlds/{world_id}/start`, pega el ID, y ejecuta con `{"adapter_type": "mock"}`
6. Copia el `commit_id` de la respuesta
7. Busca `POST /commits/{commit_id}/advance`, elige una opcion del paso anterior, y avanza

Cada respuesta incluye las opciones para el siguiente paso, el estado dramatico,
y el texto narrativo generado.
