# Guia: Docker y Docker Compose

> Guia para principiantes. No necesitas experiencia previa con Docker.

---

## 1. Que es Docker

Imagina que quieres ejecutar esta aplicacion en otra computadora. Necesitarias
instalar Python 3.11, PostgreSQL 16, las dependencias del proyecto, configurar
variables de entorno... y aun asi algo podria fallar porque la otra maquina
tiene versiones diferentes. Este es el clasico problema de "en mi maquina
funciona".

**Docker** resuelve esto empaquetando la aplicacion junto con todo lo que
necesita (sistema operativo, librerias, configuracion) dentro de un
**contenedor**: una caja aislada que se ejecuta de forma identica en cualquier
maquina.

### Conceptos clave

- **Imagen**: es la receta o plano. Define que contiene el contenedor
  (por ejemplo, `postgres:16-alpine` es una imagen con PostgreSQL 16 listo
  para usar). Las imagenes no cambian.
- **Contenedor**: es una instancia ejecutandose a partir de una imagen.
  Puedes tener multiples contenedores de la misma imagen.
- **Contenedor vs Maquina Virtual**: una maquina virtual emula hardware
  completo y tiene su propio sistema operativo. Un contenedor comparte el
  kernel del sistema host, asi que es mucho mas ligero (se levanta en
  segundos, no en minutos).

---

## 2. Que es Docker Compose

En este proyecto necesitamos **5 servicios** trabajando juntos: la app,
una base de datos, un servidor de IA, cache, y un explorador de base de datos.
Levantar cada uno manualmente seria tedioso.

**Docker Compose** permite definir todos los servicios en un solo archivo
(`docker-compose.yml`) y levantarlos con un solo comando:

```bash
docker-compose up -d
```

El flag `-d` significa "detached" (en segundo plano). Sin el, los logs
aparecen en tu terminal y al cerrarla se detienen los servicios.

---

## 3. Los 5 servicios del proyecto

Nuestro `docker-compose.yml` define estos servicios:

| Servicio   | Imagen                  | Puerto externo | Para que sirve                  |
|------------|-------------------------|----------------|---------------------------------|
| `app`      | Custom (`Dockerfile`)   | 8000           | FastAPI + Web UI                |
| `postgres` | `postgres:16-alpine`    | 5433           | Base de datos relacional        |
| `ollama`   | `ollama/ollama:latest`  | 11434          | Servidor de LLMs locales        |
| `redis`    | `redis:7-alpine`        | 6379           | Cache en memoria (opcional)     |
| `adminer`  | `adminer:latest`        | 8080           | UI web para explorar la base de datos |

### app

La aplicacion principal. Se construye desde el `Dockerfile` del proyecto
(no usa una imagen publica). Al iniciar, ejecuta las migraciones de base de
datos (`alembic upgrade head`) y luego levanta el servidor FastAPI en el
puerto 8000. Depende de que PostgreSQL este saludable antes de arrancar.

### postgres

Base de datos PostgreSQL 16 (variante Alpine, mas ligera). Almacena los
mundos, eventos, commits y ramas narrativas. El puerto externo es **5433**
(no el 5432 por defecto) para evitar conflictos si ya tienes PostgreSQL
instalado localmente. Dentro de la red Docker, los otros contenedores lo
acceden por el puerto 5432 estandar.

### ollama

Servidor de modelos de lenguaje locales. Al iniciar, descarga automaticamente
el modelo `gemma3:4b` usando el script `scripts/ollama-entrypoint.sh`. La
primera vez puede tardar varios minutos dependiendo de tu conexion. Despues
el modelo queda guardado en un volumen persistente.

### redis

Cache en memoria para datos temporales. Es opcional: la aplicacion funciona
sin el, pero mejora el rendimiento al evitar consultas repetidas a la base
de datos.

### adminer

Interfaz web para explorar la base de datos PostgreSQL sin herramientas
externas. Util para ver tablas, ejecutar queries SQL y verificar que los
datos se estan guardando correctamente.

---

## 4. Comandos esenciales

```bash
# Levantar todos los servicios en segundo plano
docker-compose up -d

# Levantar solo la app y la base de datos (sin Ollama ni Redis)
docker-compose up -d app postgres

# Ver los logs de un servicio en tiempo real (Ctrl+C para salir)
docker-compose logs -f app

# Ver el estado de todos los servicios
docker-compose ps

# Detener todos los servicios (conserva los datos)
docker-compose down

# Detener y borrar volumenes (BORRA todos los datos persistidos)
docker-compose down -v

# Reiniciar un servicio especifico
docker-compose restart app

# Reconstruir la imagen de la app despues de cambios en el codigo
docker-compose build app
docker-compose up -d app
```

---

## 5. Variables de entorno

El servicio `app` usa estas variables de entorno para saber como conectarse
a los demas servicios:

| Variable              | Valor en docker-compose.yml                                      | Descripcion                                   |
|-----------------------|------------------------------------------------------------------|-----------------------------------------------|
| `DATABASE_URL`        | `postgresql+asyncpg://cne_user:cne_password_dev@postgres:5432/cne_db` | Cadena de conexion a PostgreSQL               |
| `DEFAULT_AI_ADAPTER`  | `ollama`                                                         | Adapter de IA por defecto (`ollama`, `anthropic`, `mock`) |
| `OLLAMA_BASE_URL`     | `http://ollama:11434`                                            | URL interna del servidor Ollama               |
| `OLLAMA_MODEL`        | `gemma3:4b`                                                      | Modelo a descargar y usar                     |
| `REDIS_URL`           | `redis://redis:6379`                                             | Conexion a Redis para cache                   |

Nota que las URLs usan nombres de servicio (`postgres`, `ollama`, `redis`)
en lugar de `localhost`. Esto es porque Docker Compose crea una red interna
donde cada servicio se identifica por su nombre.

### Archivo `.env`

Puedes crear un archivo `.env` en la raiz del proyecto para sobreescribir
variables sin modificar el `docker-compose.yml`. Por ejemplo, para usar
Claude en vez de Ollama:

```env
DEFAULT_AI_ADAPTER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Revisa `.env.example` si existe para ver todas las variables disponibles.

---

## 6. Volumenes

Los **volumenes** son almacenamiento persistente. Sin ellos, los datos dentro
de un contenedor se pierden al detenerlo. El proyecto define 3 volumenes:

| Volumen          | Servicio   | Que guarda                              |
|------------------|------------|-----------------------------------------|
| `postgres_data`  | `postgres` | Tablas, indices y datos de la base de datos |
| `redis_data`     | `redis`    | Cache persistido a disco                |
| `ollama_data`    | `ollama`   | Modelos descargados (varios GB)         |

### Importante sobre `down` vs `down -v`

```bash
# Detiene contenedores pero CONSERVA los volumenes (tus datos siguen ahi)
docker-compose down

# Detiene contenedores Y BORRA los volumenes (pierdes todos los datos)
docker-compose down -v
```

Usa `down -v` solo cuando quieras empezar de cero (por ejemplo, si la base
de datos quedo en un estado inconsistente y prefieres recrearla).

---

## 7. Healthchecks

Docker necesita saber cuando un servicio esta **realmente listo** para
recibir conexiones, no solo cuando el contenedor inicio. Para esto se usan
healthchecks:

| Servicio   | Comando de verificacion                         | Intervalo |
|------------|------------------------------------------------|-----------|
| `postgres` | `pg_isready -U cne_user -d cne_db`             | 10s       |
| `redis`    | `redis-cli ping`                                | 10s       |
| `ollama`   | `curl -sf http://localhost:11434/api/tags`       | 15s       |

El servicio `app` tiene esta configuracion en su `depends_on`:

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

Esto significa que Docker **no inicia la app** hasta que PostgreSQL reporte
que esta saludable. Asi se evita que la app intente conectarse a una base
de datos que aun no esta lista.

---

## 8. URLs de acceso

Una vez que los servicios estan corriendo (`docker-compose up -d`):

```
Web UI:     http://localhost:8000/play     # Interfaz web del motor narrativo
API Docs:   http://localhost:8000/docs     # Documentacion interactiva (Swagger)
Adminer:    http://localhost:8080          # Explorador de base de datos
PostgreSQL: localhost:5433                 # Conexion directa (ej. con DBeaver)
Ollama:     http://localhost:11434         # API del servidor de modelos
```

---

## 9. Troubleshooting

### El puerto ya esta en uso

```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

Algo mas esta usando ese puerto. Para identificarlo:

```bash
# Linux/Mac
lsof -i :8000

# Windows (PowerShell)
netstat -ano | findstr :8000
```

Solucion: detener el otro proceso, o cambiar el puerto en `docker-compose.yml`
(por ejemplo, `"8001:8000"` para acceder por el puerto 8001).

### Un servicio no arranca

Revisa sus logs para ver el error:

```bash
docker-compose logs postgres
docker-compose logs app
```

### Se perdieron los datos de la base de datos

Probablemente ejecutaste `docker-compose down -v`. El flag `-v` borra los
volumenes. Usa solo `docker-compose down` para conservar datos.

### Ollama no tiene el modelo descargado

El script `scripts/ollama-entrypoint.sh` descarga `gemma3:4b` automaticamente
al iniciar. Si fallo la descarga (por ejemplo, por falta de conexion), reinicia
el servicio:

```bash
docker-compose restart ollama
docker-compose logs -f ollama
```

### La app no conecta a PostgreSQL

Verifica que PostgreSQL este saludable:

```bash
docker-compose ps
```

La columna de estado debe mostrar `healthy` para `postgres`. Si dice
`starting` o `unhealthy`, espera o revisa los logs.

---

## 10. Pruebalo tu mismo

Si es tu primera vez con Docker, prueba estos pasos:

**Paso 1**: Levanta solo la base de datos y Redis (son los mas rapidos):

```bash
docker-compose up -d postgres redis adminer
```

**Paso 2**: Verifica que estan corriendo:

```bash
docker-compose ps
```

**Paso 3**: Abre Adminer en tu navegador: [http://localhost:8080](http://localhost:8080)

Usa estos datos para conectarte:

| Campo       | Valor              |
|-------------|--------------------|
| Sistema     | PostgreSQL         |
| Servidor    | postgres           |
| Usuario     | cne_user           |
| Contrasena  | cne_password_dev   |
| Base de datos | cne_db           |

**Paso 4**: Observa los logs de PostgreSQL:

```bash
docker-compose logs postgres
```

Deberias ver mensajes indicando que la base de datos esta lista para
aceptar conexiones.

**Paso 5**: Cuando termines, detener todo:

```bash
docker-compose down
```

---

## Referencias cruzadas

- Para entender como la app se conecta a PostgreSQL, lee `guia_persistencia.md`
- Para la estructura de la API REST, consulta `integration_guide.md`
- Para el flujo completo del motor narrativo, consulta `DIAGRAMA_FLUJO.md`
