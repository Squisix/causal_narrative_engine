# Guia: Testing con pytest

Esta guia explica como funciona pytest y como estan organizados los tests del
Causal Narrative Engine (CNE). Si nunca has escrito tests en Python, este es
tu punto de partida.

---

## 1. Que es pytest

pytest es el framework de testing mas popular de Python. A diferencia de otros
frameworks (como JUnit en Java), no necesitas clases especiales ni metodos con
nombres raros. Funciona con funciones normales y el `assert` nativo de Python.

**Tres reglas de descubrimiento automatico:**

1. Los archivos deben llamarse `test_*.py`
2. Las funciones deben llamarse `test_*`
3. Se ejecuta con `python -m pytest tests/ -v`

pytest encuentra tus tests automaticamente, los ejecuta, y te dice cuales
pasaron y cuales fallaron.

---

## 2. Estructura de un test

Todo test sigue el patron **Arrange / Act / Assert**:

```python
from cne_core.models.world import Entity, EntityType

def test_entity_is_alive_by_default():
    # Arrange: preparar los datos
    lyra = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100, "alive": True}
    )

    # Act: ejecutar lo que quieres probar
    result = lyra.is_alive

    # Assert: verificar el resultado
    assert result is True
```

Ejemplo real del proyecto (`tests/test_fase1.py`) -- validando que el grafo
causal detecta ciclos correctamente:

```python
from cne_core.engine.causal_validator import CausalValidator, CausalCycleError

def test_causal_validator():
    validator = CausalValidator()

    # Registrar eventos y crear cadena: e1 -> e2 -> e3
    validator.add_event("e1")
    validator.add_event("e2")
    validator.add_event("e3")
    validator.add_edge("e1", "e2")
    validator.add_edge("e2", "e3")

    assert validator.is_dag(), "El grafo debe ser un DAG"

    # Intentar crear ciclo e3 -> e1 debe lanzar error
    cycle_detected = False
    try:
        validator.add_edge("e3", "e1")
    except CausalCycleError:
        cycle_detected = True

    assert cycle_detected, "Debe detectar el ciclo e3->e1"
```

---

## 3. Fixtures

Las fixtures son funciones reutilizables que preparan datos o recursos para
tus tests. Se definen con el decorador `@pytest.fixture` y se inyectan como
parametros de la funcion de test.

### Fixture basica

Ejemplo real de `tests/test_adapters.py`:

```python
@pytest.fixture
def mock_adapter():
    return MockAdapter(deterministic=True, seed=42)

@pytest.fixture
def world_with_entities():
    lyra = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100, "influence": 70},
    )
    return WorldDefinition(
        name="Reino de Eldoria",
        context="Un reino medieval en crisis politica",
        protagonist="Princesa Lyra",
        era="Medieval",
        tone=NarrativeTone.DARK,
        initial_entities=[lyra],
    )

# pytest inyecta automaticamente las fixtures como parametros
async def test_basic_generation(world_with_entities, mock_adapter):
    context = _make_context(world_with_entities)
    proposal = await mock_adapter.generate_narrative(context)
    assert proposal is not None
    assert len(proposal.narrative_text) > 50
```

### `yield` para cleanup

Si necesitas limpiar recursos despues del test, usa `yield`. Todo lo que esta
antes de `yield` es setup; todo lo que esta despues es teardown.

Ejemplo real de `tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def _reset_engine_cache():
    """Clear the narrative service engine cache between tests."""
    yield
    try:
        from api.services.narrative_service_v2 import _engine_cache
        _engine_cache.clear()
    except ImportError:
        pass
```

### Parametros importantes

- **`autouse=True`**: la fixture se ejecuta automaticamente para cada test,
  sin necesidad de pasarla como parametro.
- **`scope="session"`**: la fixture se ejecuta una sola vez para toda la sesion
  de tests (en vez de una vez por cada test).

Ejemplo real de `tests/conftest.py` -- limpiar la conexion a la base de datos
una sola vez al final de todos los tests:

```python
@pytest.fixture(scope="session", autouse=True)
async def _dispose_db_engine():
    """Dispose the global database engine at the end of the test session."""
    yield
    try:
        import persistence.database as db_module
        if db_module._global_engine is not None:
            await db_module._global_engine.dispose()
            db_module._global_engine = None
    except ImportError:
        pass
```

---

## 4. pytest-asyncio

El proyecto usa funciones async (`async def`) para la persistencia y la API.
pytest-asyncio permite testear estas funciones directamente.

**Configuracion clave en `pyproject.toml`:**

```toml
asyncio_mode = "auto"
```

Con `asyncio_mode = "auto"`, todas las funciones de test `async def` se
detectan automaticamente -- no necesitas agregar `@pytest.mark.asyncio` a
cada una (aunque puedes hacerlo para ser explicito).

Ejemplo real de `tests/test_api.py`:

```python
@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
```

> Para entender async/await en profundidad, lee `guia_python.md`
> (seccion async/await).

---

## 5. Marks y skipif

Los markers permiten etiquetar tests y ejecutar solo un subconjunto.

### Markers personalizados del proyecto

Definidos en `pyproject.toml`:

```toml
markers = [
    "fase1: Tests de Fase 1 (Core Engine en memoria)",
    "fase2: Tests de Fase 2 (Persistencia con PostgreSQL)",
    "fase3: Tests de Fase 3 (AI Adapter)",
    "integration: Tests de integración (requieren servicios externos)",
    "anthropic_api: Tests que requieren API key de Anthropic (consumen tokens)",
]
```

### `@pytest.mark.skipif`

Salta tests condicionalmente. El proyecto lo usa para los tests de Anthropic
que requieren una API key real (y cuestan dinero):

```python
def check_api_key():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip(
            "ANTHROPIC_API_KEY no esta configurada. "
            "Configura tu .env para ejecutar estos tests."
        )
    return api_key
```

### Aplicar un marker a todo un archivo

En `tests/test_anthropic_adapter.py`, todos los tests llevan el marker
`anthropic_api` gracias a esta linea al inicio del archivo:

```python
pytestmark = pytest.mark.anthropic_api
```

---

## 6. Los 5 archivos de test

| Archivo | Que testea | Requiere Docker | Requiere API Key |
|---------|------------|-----------------|------------------|
| `test_fase1.py` | Core Engine: DAG, SDMM, StateMachine, P1-P4 | No | No |
| `test_adapters.py` | MockAdapter, entity creation, 5-tuple | No | No |
| `test_api.py` | API REST completa (17 tests) | Si (PostgreSQL) | No |
| `test_persistence_integration.py` | PostgreSQLRepository | Si (PostgreSQL) | No |
| `test_anthropic_adapter.py` | Real Claude API generation | No | Si (cuesta dinero) |

**`test_fase1.py`** es el test mas importante: verifica las 4 propiedades
formales del motor (Causalidad, Determinismo, Versionado, Consistencia) sin
ninguna dependencia externa. Si este test pasa, el core del motor funciona.

**`test_adapters.py`** verifica que los adapters de IA generan propuestas
validas y que el motor las procesa correctamente. Usa `MockAdapter`, asi que
tampoco necesita nada externo.

**`test_api.py`** monta la aplicacion FastAPI en memoria y prueba cada
endpoint. Requiere PostgreSQL corriendo.

**`test_persistence_integration.py`** verifica que todas las tablas de la BD
se llenan correctamente al generar una narrativa.

**`test_anthropic_adapter.py`** se conecta a la API real de Claude y verifica
que las respuestas cumplen el contrato. Solo se ejecuta con `-m anthropic_api`.

---

## 7. MockAdapter vs integracion

### MockAdapter (para logica de negocio)

- **Determinista**: misma semilla = mismos resultados
- **Sin dependencias externas**: no necesita API keys, internet, ni Docker
- **Rapido**: respuestas instantaneas
- Ideal para probar la logica del motor, no la calidad de la IA

```python
from adapters.mock_adapter import MockAdapter

adapter = MockAdapter(deterministic=True, seed=42)
```

### Tests de integracion (para el stack completo)

- Usan PostgreSQL real
- Prueban que la persistencia, el motor y la API funcionan juntos
- Mas lentos, pero verifican que todo conecta correctamente

### Nota: `adapter_type` en tests de API

Por defecto, los endpoints de la API (como `/advance`) usan `"adapter_type": "mock"`. Esto significa que los tests son rápidos y seguros sin necesidad de dependencias externas.

Si deseas probar la integración con un modelo real como Ollama, puedes especificar `"adapter_type": "ollama"` en el body del request:

```python
# Usa Ollama (requiere servidor local de Ollama corriendo)
r = await client.post(
    f"/commits/{commit_id}/advance",
    json={"choice": choice_text, "adapter_type": "ollama"},
)

# Por defecto, si se omite, se usa el MockAdapter:
r = await client.post(
    f"/commits/{commit_id}/advance",
    json={"choice": choice_text},  # adapter_type default = "mock"
)
```

---

## 8. httpx.AsyncClient para tests de API

FastAPI no necesita un servidor real corriendo para sus tests. Se usa
`httpx.AsyncClient` con `ASGITransport` para montar la app en memoria:

```python
from httpx import AsyncClient, ASGITransport
from api.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

Ejemplo real de test (`tests/test_api.py`):

```python
async def test_create_world(client):
    r = await client.post("/worlds", json={
        "name": "API Test World",
        "context": "Un reino medieval para testing",
        "protagonist": "El heroe",
        "era": "Medieval",
        "tone": "dark",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "API Test World"
```

El fixture `client` inyecta el `AsyncClient` automaticamente. El test hace
requests HTTP como si fuera un cliente real, pero todo corre en memoria.

---

## 9. Comandos para correr tests

```bash
# Rapido (sin dependencias externas)
pytest tests/test_fase1.py tests/test_adapters.py -v

# Con Docker (API + persistencia)
docker-compose up -d postgres
alembic upgrade head
pytest tests/ -v

# Excluir tests que requieren API key de Anthropic
pytest -m "not anthropic_api" -v

# Solo un test especifico
pytest tests/test_fase1.py::test_causal_validator -v

# Coverage (incluido por defecto en la configuracion)
pytest --cov=cne_core --cov=adapters --cov-report=html -v

# Solo tests de una fase
pytest -m fase1 -v
```

> Para levantar PostgreSQL con Docker, lee `guia_docker.md`.

---

## 10. Configuracion en pyproject.toml

Toda la configuracion de pytest vive en `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--cov=cne_core",
    "--cov=persistence",
    "--cov=adapters",
    "--cov-report=term-missing",
    "--cov-report=html",
]
markers = [
    "fase1: Tests de Fase 1 (Core Engine en memoria)",
    "fase2: Tests de Fase 2 (Persistencia con PostgreSQL)",
    "fase3: Tests de Fase 3 (AI Adapter)",
    "integration: Tests de integración (requieren servicios externos)",
    "anthropic_api: Tests que requieren API key de Anthropic (consumen tokens)",
]
```

**Opciones importantes:**
- `asyncio_mode = "auto"` -- detecta tests async automaticamente
- `--strict-markers` -- falla si usas un marker no declarado (evita typos)
- `--cov=cne_core` -- mide cobertura de codigo automaticamente
- `-ra` -- muestra un resumen de tests fallidos al final

---

## 11. Pruebalo tu mismo

**Paso 1**: Ejecuta los tests del core (cero dependencias):

```bash
pytest tests/test_fase1.py -v
```

Deberias ver algo como:

```
tests/test_fase1.py::test_causal_validator PASSED
tests/test_fase1.py::test_dramatic_engine PASSED
tests/test_fase1.py::test_full_story PASSED
```

**Paso 2**: Lee `tests/test_fase1.py` completo. Es el mejor ejemplo de como
se testean las 4 propiedades formales del motor.

**Paso 3**: Intenta agregar tu propio test. Crea un archivo
`tests/test_mi_primer_test.py`:

```python
from cne_core.models.world import Entity, EntityType

def test_entity_creation():
    """Mi primer test: verificar que una entidad se crea correctamente."""
    hero = Entity(
        name="Kael",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100, "alive": True}
    )

    assert hero.name == "Kael"
    assert hero.entity_type == EntityType.CHARACTER
    assert hero.attributes["health"] == 100
    assert hero.is_alive is True
```

Ejecutalo con:

```bash
pytest tests/test_mi_primer_test.py -v
```

Si ves `PASSED`, felicidades -- ya sabes testear con pytest.
