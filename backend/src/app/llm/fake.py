from __future__ import annotations

from copy import deepcopy

from app.llm.providers import LLMHealth, LLMHealthStatus, LLMProvider, LLMRequest
from app.llm.schemas import AIOutput

UNAVAILABLE_FALLBACK = AIOutput(
    answer="AI explanation is currently unavailable. Please use the structured evaluation result and cited evidence.",
    resultStatus="LLM_UNAVAILABLE",
)


class FakeLLMProvider:
    provider_name = "fake"

    def __init__(self, output: AIOutput | None = None, model: str = "fake-model") -> None:
        self.output = output or UNAVAILABLE_FALLBACK
        self.model = model
        self.requests: list[LLMRequest] = []

    async def health(self) -> LLMHealth:
        return LLMHealth(status=LLMHealthStatus.READY, provider=self.provider_name, model=self.model)

    async def generate(self, request: LLMRequest) -> AIOutput:
        self.requests.append(request)
        return AIOutput.model_validate(deepcopy(self.output.model_dump(by_alias=True)))


class TemplateLLMProvider:
    provider_name = "template"

    def __init__(self, model: str = "template-model") -> None:
        self.model = model

    async def health(self) -> LLMHealth:
        return LLMHealth(status=LLMHealthStatus.READY, provider=self.provider_name, model=self.model)

    async def generate(self, request: LLMRequest) -> AIOutput:
        _ = request
        return UNAVAILABLE_FALLBACK


def ensure_provider_protocol(_provider: LLMProvider) -> None:
    return None
