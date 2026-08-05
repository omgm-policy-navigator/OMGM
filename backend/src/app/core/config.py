from __future__ import annotations

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigurationError

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    cors_allowed_origins: str = "http://localhost:5173"
    database_url: str
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    ollama_base_url: str = "http://localhost:11434"
    ollama_generation_model: str = "qwen3:4b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    llm_timeout_seconds: int = Field(default=30, gt=0)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        log_level = value.strip().upper()
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL.")
        return log_level

    @field_validator("app_env", "backend_host", "database_url")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be empty.")
        return stripped

    @classmethod
    def from_env(cls) -> AppConfig:
        try:
            return cls()
        except ValidationError as exc:
            raise ConfigurationError("Backend configuration is invalid.") from exc
