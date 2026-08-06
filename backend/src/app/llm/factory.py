from __future__ import annotations

import logging

from app.core.config import AppConfig
from app.llm.fake import FakeLLMProvider, TemplateLLMProvider
from app.llm.ollama import OllamaLLMProvider
from app.llm.providers import LLMHealthStatus, LLMProvider

logger = logging.getLogger(__name__)


def create_llm_provider(config: AppConfig) -> LLMProvider:
    if config.llm_provider == "fake":
        return FakeLLMProvider(model="fake-model")
    if config.llm_provider == "template":
        return TemplateLLMProvider(model="template-model")
    return OllamaLLMProvider(
        base_url=config.ollama_base_url,
        model=config.ollama_generation_model,
        timeout_seconds=config.llm_timeout_seconds,
        temperature=config.llm_temperature,
    )


async def create_available_llm_provider(config: AppConfig) -> LLMProvider:
    provider = create_llm_provider(config)
    health = await provider.health()
    if health.status == LLMHealthStatus.READY:
        return provider

    close_provider = getattr(provider, "aclose", None)
    if close_provider is not None:
        await close_provider()

    logger.warning(
        "LLM provider is not ready; using template fallback",
        extra={"provider": health.provider, "model": health.model, "status": health.status},
    )
    return TemplateLLMProvider(model="template-model")
