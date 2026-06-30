"""
api/config.py - Configuración de la API

Lee configuración desde variables de entorno.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración de la API.

    Se carga automáticamente desde .env si existe.
    """
    # API
    app_name: str = "Causal Narrative Engine API"
    app_version: str = "0.3.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: list[str] = ["*"]  # En producción, especificar dominios exactos

    # Database (Fase 2 - PostgreSQL)
    database_url: str = "postgresql+asyncpg://cne_user:cne_password@localhost:5432/cne_db"

    # AI Adapters
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_max_tokens: int = 2048
    anthropic_temperature: float = 0.7

    # Default adapter ("mock" o "anthropic")
    default_ai_adapter: str = "mock"

    # Session management
    session_timeout_minutes: int = 60
    max_sessions_per_world: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna la configuración global.

    Usa @lru_cache para crear una sola instancia (singleton pattern).
    """
    return Settings()
