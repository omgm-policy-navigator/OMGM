from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from app.llm.schemas import AIOutput


class LLMHealthStatus(StrEnum):
    READY = "READY"
    MODEL_NOT_INSTALLED = "MODEL_NOT_INSTALLED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class LLMHealth:
    status: LLMHealthStatus
    provider: str
    model: str


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    system: str | None = None


class LLMError(Exception):
    """Base exception for provider failures hidden behind fallback responses."""


class LLMUnavailableError(LLMError):
    pass


class LLMModelNotInstalledError(LLMUnavailableError):
    pass


class LLMTimeoutError(LLMUnavailableError):
    pass


class LLMInvalidJSONError(LLMError):
    pass


@runtime_checkable
class LLMProvider(Protocol):
    async def health(self) -> LLMHealth:
        """Return provider health without raising provider-specific exceptions."""

    async def check_health(self) -> bool:
        """Return True when this provider is ready for generation."""

    async def generate(self, request: LLMRequest) -> AIOutput:
        """Generate and validate an AIOutput response."""
