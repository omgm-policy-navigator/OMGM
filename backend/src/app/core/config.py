from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.errors import ConfigurationError

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class AppConfig:
    app_env: str = "local"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"
    cors_allowed_origins: str = "http://localhost:5173"
    database_url: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_generation_model: str = "qwen3:4b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    llm_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "AppConfig":
        app_env = os.getenv("APP_ENV", "local").strip() or "local"
        backend_host = os.getenv("BACKEND_HOST", "0.0.0.0").strip() or "0.0.0.0"
        log_level = (os.getenv("LOG_LEVEL", "INFO").strip() or "INFO").upper()
        raw_port = os.getenv("BACKEND_PORT", "8000").strip() or "8000"
        raw_llm_timeout = os.getenv("LLM_TIMEOUT_SECONDS", "30").strip() or "30"

        if log_level not in VALID_LOG_LEVELS:
            raise ConfigurationError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL.")

        try:
            backend_port = int(raw_port)
        except ValueError as exc:
            raise ConfigurationError("BACKEND_PORT must be an integer.") from exc

        if not 1 <= backend_port <= 65535:
            raise ConfigurationError("BACKEND_PORT must be between 1 and 65535.")

        try:
            llm_timeout_seconds = int(raw_llm_timeout)
        except ValueError as exc:
            raise ConfigurationError("LLM_TIMEOUT_SECONDS must be an integer.") from exc

        if llm_timeout_seconds <= 0:
            raise ConfigurationError("LLM_TIMEOUT_SECONDS must be positive.")

        return cls(
            app_env=app_env,
            backend_host=backend_host,
            backend_port=backend_port,
            log_level=log_level,
            cors_allowed_origins=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173"),
            database_url=os.getenv("DATABASE_URL", ""),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_generation_model=os.getenv("OLLAMA_GENERATION_MODEL", "qwen3:4b"),
            ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b"),
            llm_timeout_seconds=llm_timeout_seconds,
        )
