"""
api/config.py - API Configuration

Reads configuration from environment variables.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    API Configuration.

    Automatically loaded from .env if it exists.
    """
    # API
    app_name: str = "Causal Narrative Engine API"
    app_version: str = "0.3.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: list[str] = ["*"]  # In production, specify exact domains

    # Database (Fase 2 - PostgreSQL)
    database_url: str = "postgresql+asyncpg://cne_user:cne_password@localhost:5432/cne_db"

    # AI Adapters
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_max_tokens: int = 2048
    anthropic_temperature: float = 0.7

    # Ollama (local LLMs)
    ollama_model: str = "gemma3:4b"
    ollama_base_url: str = "http://localhost:11434"
    ollama_temperature: float = 0.7

    # Default adapter ("mock", "anthropic", or "ollama")
    default_ai_adapter: str = "mock"

    # Redis (cache)
    redis_url: str | None = None
    redis_ttl_trunk: int = 3600
    redis_ttl_world: int = 1800
    redis_ttl_choices: int = 3600

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
    Returns the global configuration.

    Uses @lru_cache to create a single instance (singleton pattern).
    """
    return Settings()
