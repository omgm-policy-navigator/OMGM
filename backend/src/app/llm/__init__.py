"""LLM boundary for Ollama-facing helpers and DTOs."""

from app.llm.factory import create_llm_provider
from app.llm.fake import FakeLLMProvider, TemplateLLMProvider
from app.llm.ollama import OllamaLLMProvider
from app.llm.providers import (
    LLMError,
    LLMHealth,
    LLMHealthStatus,
    LLMInvalidJSONError,
    LLMModelNotInstalledError,
    LLMProvider,
    LLMRequest,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.schemas import (
    AICitation,
    AIConditionReference,
    AINextQuestion,
    AIOutput,
    AIResultStatus,
)

__all__ = [
    "AIConditionReference",
    "AICitation",
    "AINextQuestion",
    "AIOutput",
    "AIResultStatus",
    "FakeLLMProvider",
    "LLMError",
    "LLMHealth",
    "LLMHealthStatus",
    "LLMInvalidJSONError",
    "LLMModelNotInstalledError",
    "LLMProvider",
    "LLMRequest",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "OllamaLLMProvider",
    "TemplateLLMProvider",
    "create_llm_provider",
]
