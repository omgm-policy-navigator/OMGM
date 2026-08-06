from __future__ import annotations

import logging

from app.llm.fake import UNAVAILABLE_FALLBACK, TemplateLLMProvider
from app.llm.providers import LLMProvider, LLMRequest
from app.llm.schemas import AIOutput

logger = logging.getLogger(__name__)


class RobustLLMManager:
    def __init__(self, primary_provider: LLMProvider, fallback_provider: LLMProvider | None = None) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider or TemplateLLMProvider()

    async def generate(self, request: LLMRequest) -> AIOutput:
        try:
            return await self.primary_provider.generate(request)
        except Exception as primary_exc:
            logger.warning("Primary LLM provider failed; switching to fallback provider", exc_info=primary_exc)

        try:
            fallback_output = await self.fallback_provider.generate(request)
            return fallback_output.model_copy(update={"is_fallback": True})
        except Exception as fallback_exc:
            logger.error("Fallback LLM provider failed; returning static safety net", exc_info=fallback_exc)
            return static_safety_output()


def static_safety_output() -> AIOutput:
    return UNAVAILABLE_FALLBACK.model_copy(update={"is_fallback": True})