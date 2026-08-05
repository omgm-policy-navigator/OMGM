from __future__ import annotations

from app.core.config import AppConfig
from app.llm.fake import FakeLLMProvider, TemplateLLMProvider
from app.llm.ollama import OllamaLLMProvider
from app.llm.providers import LLMProvider


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
