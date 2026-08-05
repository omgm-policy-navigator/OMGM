from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    app_env: Literal["local", "test", "staging", "production"] = "local"
    backend_host: str = Field(default="0.0.0.0", min_length=1)
    backend_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_allowed_origins: str = "http://localhost:5173"
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://marry_policy:local@localhost:5432/marry_policy"
    )
    ollama_base_url: str = "http://localhost:11434"
    ollama_generation_model: str = "qwen3:4b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    llm_timeout_seconds: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        return str(self.database_url)

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls()


@lru_cache
def get_config() -> AppConfig:
    return AppConfig.from_env()
