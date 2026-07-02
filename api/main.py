"""
api/main.py - FastAPI application

Aplicación principal de la API REST.

Ejecutar:
    uvicorn api.main:app --reload
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from api.config import get_settings
from api.routers import health, worlds, narrative


# ── Lifespan events ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja startup y shutdown de la aplicación.
    """
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Default AI adapter: {settings.default_ai_adapter}")

    yield

    # Shutdown
    print("Shutting down...")


# ── FastAPI app ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Causal Narrative Engine API",
    description="""
# Causal Narrative Engine - REST API

Motor narrativo basado en causalidad formal para generar historias ramificadas con IA.

## Características

- **Worlds**: Define universos narrativos (semillas)
- **Narrative Flow**: Genera narrativa con IA y avanza la historia
- **Dramatic System**: Vector de 7 dimensiones (tensión, esperanza, caos, etc.)
- **Branching**: Versionado Git-like de decisiones
- **AI Adapters**: MockAdapter (gratis) y Claude (Anthropic)

## Flujo típico

1. `POST /worlds` - Crear mundo
2. `POST /worlds/{id}/start` - Iniciar narrativa
3. `POST /commits/{id}/advance` - Tomar decisión
4. Repetir paso 3...

## Docs interactivos

- Swagger UI: `/docs`
- ReDoc: `/redoc`
    """,
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ────────────────────────────────────────────────────────────────────────

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(worlds.router)
app.include_router(narrative.router)


# ── Root endpoint ───────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "Causal Narrative Engine API",
        "version": "0.3.0",
        "docs": "/docs",
        "play": "/play",
        "health": "/health",
    }


# ── Web UI ─────────────────────────────────────────────────────────────────────

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")

if os.path.isdir(WEB_DIR):
    @app.get("/play")
    async def play_ui():
        return FileResponse(os.path.join(WEB_DIR, "index.html"))

    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web-static")


# ── Main (para ejecución directa) ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
