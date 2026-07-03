# CNE Docker Guide

This guide explains how to spin up external services (PostgreSQL, Redis cache, and Ollama) using Docker and Docker Compose.

---

## Prerequisites
- Docker installed on your host machine.
- Docker Compose installed.

---

## Services Overview

The project includes a pre-configured `docker-compose.yml` file with three services:
1. **PostgreSQL** (`cne_db`): Database containing worlds, entities, events, commits, and relationships.
2. **Redis** (`cne_cache`): Optional caching layer to accelerate world and commit graph reads.
3. **Ollama** (`ollama`): Optional local LLM backend for running open-source models (such as `gemma2` or `llama3`) for offline generation.

---

## Running the Services

### 1. Start all services
To spin up all configured services in the background, run:
```bash
docker-compose up -d
```

### 2. Verify statuses
To check if the containers are running healthy:
```bash
docker-compose ps
```

### 3. Retrieve logs
To inspect real-time outputs of a specific service (e.g. PostgreSQL):
```bash
docker-compose logs -f postgres
```

---

## PostgreSQL Configuration
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `cne_db`
- **Username**: `cne_user`
- **Password**: `cne_password`

### Initializing Tables (Migrations)
After starting PostgreSQL, run the Alembic database migrations to upgrade to the latest schema:
```bash
alembic upgrade head
```

---

## Ollama Local Models
If you wish to use the Ollama service, download the desired model into the container before running the server:
```bash
docker-compose exec ollama ollama pull gemma2:2b
```
You can then configure CNE to use the Ollama adapter type.
