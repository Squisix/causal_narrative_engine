# Quickstart — Fase 2 en 5 minutos

## ¿Qué necesitas?

- Python 3.11+
- Docker Desktop (para PostgreSQL)
- Git (para clonar el repo)

---

## Paso 1: Instalar dependencias

```bash
# Clonar el repo (si aún no lo hiciste)
cd causal_narrative_engine

# Instalar el paquete con dependencias de Fase 2
pip install -e ".[persistence,dev]"
```

**Qué instaló:**
- `sqlalchemy[asyncio]` — ORM async
- `alembic` — Migraciones
- `asyncpg` — Driver PostgreSQL async
- `pytest-asyncio` — Tests async

---

## Paso 2: Levantar PostgreSQL

```bash
# Levantar servicios con Docker Compose
docker-compose up -d

# Verificar que esté corriendo
docker ps
```

**Qué levantó:**
- PostgreSQL 16 en `localhost:5432`
- Adminer (UI web) en `http://localhost:8080`
- Redis en `localhost:6379` (para Fase 4+)

---

## Paso 3: Aplicar migraciones

```bash
# Crear todas las tablas
alembic upgrade head

# Verificar
alembic current
```

**Qué creó:**
- 10 tablas (worlds, events, commits, dramatic_states, etc.)
- Índices optimizados para queries causales
- Constraints para validar rango de medidores [0-100]

---

## Paso 4: Ejecutar el ejemplo

```bash
# Ejecutar ejemplo completo
python examples/fase2_example.py
```

**Qué hace:**
- Crea un mundo narrativo
- Guarda 3 commits con eventos encadenados
- Valida el grafo causal (detecta ciclos)
- Muestra el arco dramático

**Salida esperada:**
```
======================================================================
CNE — Ejemplo de Fase 2: Persistencia con PostgreSQL
======================================================================

[1/7] Configurando base de datos...
✅ Conectado a PostgreSQL

[2/7] Creando mundo narrativo...
✅ Mundo guardado: 'El Reino de las Sombras' (ID: a1b2c3d4...)
   Entidades iniciales: 3
   Tono: oscuro

[3/7] Creando rama narrativa...
✅ Rama creada: 'Camino del Héroe' (ID: e5f6g7h8...)

[4/7] Construyendo historia...
   [Capítulo 0] Lyra debe decidir si regresar al reino.
   [Capítulo 1] Lyra regresa y descubre que el rey ha muerto.
   [Capítulo 2] Lyra obtiene el Cristal y descubre la verdad.

✅ Historia creada: 3 capítulos

[5/7] Recuperando historia completa...
✅ Trunk recuperado: 3 commits
   [0] Lyra debe decidir si regresar al reino.
   [1] Lyra regresa y descubre que el rey ha muerto.
   [2] Lyra obtiene el Cristal y descubre la verdad.

[6/7] Validando grafo causal...
✅ Camino causal event0 → event2: Existe
✅ Ciclo detectado correctamente: No se puede crear la arista...

[7/7] Análisis dramático...
   [Cap.0] T=45 H=50 M=70
   [Cap.1] T=50 H=45 M=80
   [Cap.2] T=60 H=55 M=65

======================================================================
RESUMEN DE FASE 2
======================================================================
✅ Mundo persistido: El Reino de las Sombras
✅ Commits guardados: 3
✅ Grafo causal validado (sin ciclos)
✅ Vector dramático rastreado
✅ Deltas de entidades registrados

Próximos pasos:
  • Fase 3: Conectar IA (Anthropic/Claude)
  • Fase 4: API REST con FastAPI
  • Fase 5: Release público + docs
======================================================================
```

---

## Paso 5: Ejecutar tests

```bash
# Todos los tests de Fase 2
pytest tests/test_fase2.py -v

# Solo un test específico
pytest tests/test_fase2.py::test_causal_cycle_detection -v
```

**Tests incluidos:**
- ✅ `test_save_and_get_world` — Persistir WorldDefinition
- ✅ `test_save_commit_and_retrieve_trunk` — Cadena de commits
- ✅ `test_causal_cycle_detection` — Detectar ciclos en DAG
- ✅ `test_dramatic_state_persistence` — Vector dramático
- ✅ `test_entity_deltas` — Deltas de entidades
- ✅ `test_list_branches` — Ramas narrativas

---

## Explorar la base de datos

### Opción 1: Adminer (UI web)

1. Ir a `http://localhost:8080`
2. Login:
   - Sistema: **PostgreSQL**
   - Servidor: **postgres**
   - Usuario: **cne_user**
   - Contraseña: **cne_password_dev**
   - Base de datos: **cne_db**
3. Explorar tablas

### Opción 2: psql (CLI)

```bash
# Conectarse a la DB desde Docker
docker exec -it cne_postgres psql -U cne_user -d cne_db

# Dentro de psql:
\dt                  # Listar tablas
\d events            # Ver esquema de tabla
SELECT * FROM worlds LIMIT 5;
```

---

## Queries útiles

### Ver todos los mundos creados

```sql
SELECT id, name, tone, created_at
FROM worlds
ORDER BY created_at DESC;
```

### Ver el grafo causal completo

```sql
SELECT
    e1.summary AS causa,
    e2.summary AS efecto,
    edge.relation_type
FROM event_edges edge
JOIN events e1 ON edge.cause_event_id = e1.id
JOIN events e2 ON edge.effect_event_id = e2.id
ORDER BY e1.depth, e2.depth;
```

### Arco dramático de una historia

```sql
SELECT
    c.depth,
    c.summary,
    ds.tension,
    ds.hope,
    ds.chaos,
    ds.mystery
FROM commits c
JOIN dramatic_states ds ON c.id = ds.commit_id
WHERE c.world_id = '<world_id>'
ORDER BY c.depth;
```

---

## Limpiar y resetear

```bash
# Detener servicios
docker-compose down

# Borrar volúmenes (RESETEA LA DB)
docker-compose down -v

# Levantar de nuevo desde cero
docker-compose up -d
alembic upgrade head
```

---

## Troubleshooting

### Error: "could not connect to server"

```bash
# Verificar que Docker esté corriendo
docker ps

# Ver logs de PostgreSQL
docker-compose logs postgres

# Reiniciar contenedor
docker-compose restart postgres
```

### Error: "relation does not exist"

```bash
# Verificar migraciones
alembic current

# Aplicar migraciones
alembic upgrade head
```

### Error: "ModuleNotFoundError: No module named 'cne_core'"

```bash
# Instalar en modo editable
pip install -e ".[persistence,dev]"
```

### Tests fallan con "database is being accessed"

```bash
# Resetear PostgreSQL
docker-compose restart postgres
```

---

## Siguiente paso: Fase 3

En Fase 3 vamos a conectar la IA:

1. Implementar `AnthropicAdapter` (Claude API)
2. Implementar `MockAIAdapter` (tests sin API key)
3. Crear `ContextBuilder` (construye el tronco activo)
4. Crear `ResponseValidator` (valida JSON de la IA)
5. Integrar todo: Core + Persistencia + IA

**Hasta ahora tienes:**
- ✅ Core Engine funcional (Fase 1)
- ✅ Persistencia en PostgreSQL (Fase 2)
- 🔲 Generación narrativa con IA (Fase 3)
- 🔲 API REST (Fase 4)
- 🔲 Release público (Fase 5)

---

## Recursos

- [CLAUDE.md](CLAUDE.md) — Documentación completa del proyecto
- [FASE2_README.md](FASE2_README.md) — Guía detallada de Fase 2
- [examples/fase2_example.py](examples/fase2_example.py) — Ejemplo completo
- [tests/test_fase2.py](tests/test_fase2.py) — Suite de tests

**¿Problemas?** Abre un issue en GitHub o revisa los logs:
```bash
docker-compose logs -f postgres
```
