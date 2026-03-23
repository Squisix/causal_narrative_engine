# Fase 2 - Pasos de Ejecución

## 1. Levantar Docker Desktop
Antes de continuar, asegúrate de que Docker Desktop esté corriendo.

Verifica con:
```bash
docker --version
docker ps
```

## 2. Levantar servicios con Docker Compose
```bash
cd C:\Users\Marguerrero\Projects\causal_narrative_engine
docker-compose up -d
```

Esto levantará:
- PostgreSQL en puerto 5433
- Redis en puerto 6379 (opcional)
- Adminer en puerto 8080 (UI para explorar DB)

Verificar que estén corriendo:
```bash
docker-compose ps
```

## 3. Aplicar migraciones con Alembic
```bash
alembic upgrade head
```

Esto creará todas las tablas necesarias en PostgreSQL.

## 4. Verificar la conexión a la base de datos
Puedes verificar en Adminer:
- URL: http://localhost:8080
- Server: postgres
- User: cne_user
- Password: (dejar vacío, trust mode)
- Database: cne_db

## 5. Ejecutar tests de Fase 2
```bash
pytest tests/test_fase2.py -v
```

O si prefieres ver más detalle:
```bash
pytest tests/test_fase2.py -v -s
```

## 6. Si hay errores

### Error: "Connection refused"
- Verifica que Docker esté corriendo
- Verifica que PostgreSQL esté levantado: `docker-compose logs postgres`

### Error: "Relation does not exist"
- Las migraciones no se aplicaron
- Ejecuta: `alembic upgrade head`

### Error en tests
- Revisa los logs: `docker-compose logs postgres`
- Verifica que la URL de conexión sea correcta en test_fase2.py

## 7. Comandos útiles

```bash
# Ver logs de PostgreSQL
docker-compose logs -f postgres

# Reiniciar servicios
docker-compose restart

# Detener servicios
docker-compose down

# Detener y borrar volúmenes (reset completo de DB)
docker-compose down -v

# Entrar al contenedor de PostgreSQL
docker exec -it cne_postgres psql -U cne_user -d cne_db

# Ver todas las tablas
docker exec -it cne_postgres psql -U cne_user -d cne_db -c "\dt"
```

## 8. Estructura de tablas esperada

Después de aplicar migraciones, deberías tener estas tablas:
- worlds
- entities
- branches
- commits
- events
- event_edges
- entity_deltas
- world_variable_deltas
- dramatic_deltas
- dramatic_state

## 9. Siguiente paso después de Fase 2

Una vez que todos los tests pasen, continuar con:
- Fase 3: AI Adapter (integración con Anthropic API)
