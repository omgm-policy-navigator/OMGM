from __future__ import annotations

import logging
from typing import Any

import httpx

from app.llm.json_parser import parse_ai_output_json
from app.llm.providers import (
    LLMHealth,
    LLMHealthStatus,
    LLMModelNotInstalledError,
    LLMRequest,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.schemas import AIOutput

logger = logging.getLogger(__name__)


class OllamaLLMProvider:
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30,
        temperature: float = 0.1,
        client: httpx.AsyncClient | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_attempts = max_attempts
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def health(self) -> LLMHealth:
        try:
            models = await self._installed_models()
        except LLMUnavailableError:
            return LLMHealth(status=LLMHealthStatus.UNAVAILABLE, provider=self.provider_name, model=self.model)

        if self.model not in models:
            logger.warning("Ollama model is not installed", extra={"model": self.model})
            return LLMHealth(
                status=LLMHealthStatus.MODEL_NOT_INSTALLED,
                provider=self.provider_name,
                model=self.model,
            )
        return LLMHealth(status=LLMHealthStatus.READY, provider=self.provider_name, model=self.model)

    async def check_health(self) -> bool:
        return (await self.health()).status == LLMHealthStatus.READY

    async def generate(self, request: LLMRequest) -> AIOutput:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": request.prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": self.temperature},
        }
        if request.system:
            payload["system"] = request.system

        try:
            response = await self._post("/api/generate", json_payload=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Ollama generation timed out.") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise LLMModelNotInstalledError("Ollama model is not installed.") from exc
            raise LLMUnavailableError("Ollama generation failed.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError("Ollama generation failed.") from exc

        raw_output = response.get("response")
        if not isinstance(raw_output, str):
            raise LLMUnavailableError("Ollama response did not include text output.")
        return parse_ai_output_json(raw_output)

    async def _installed_models(self) -> set[str]:
        try:
            response = await self._get("/api/tags")
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Ollama health check timed out.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError("Ollama health check failed.") from exc

        models = response.get("models", [])
        if not isinstance(models, list):
            raise LLMUnavailableError("Ollama tags response was invalid.")
        return {model["name"] for model in models if isinstance(model, dict) and isinstance(model.get("name"), str)}

    async def _get(self, path: str) -> dict[str, Any]:
        return await self._request_json("GET", path)

    async def _post(self, path: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request_json("POST", path, json_payload=json_payload)

    async def _request_json(
        self, method: str, path: str, json_payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = await self._client.request(method, path, json=json_payload)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self.max_attempts:
                    raise
            except httpx.HTTPStatusError as exc:
                if attempt == self.max_attempts or exc.response.status_code not in {502, 503, 504}:
                    raise
        raise RuntimeError("unreachable")
