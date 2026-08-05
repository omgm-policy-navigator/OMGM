from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.llm.providers import (
    LLMHealth,
    LLMHealthStatus,
    LLMInvalidJSONError,
    LLMModelNotInstalledError,
    LLMRequest,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.schemas import AIOutput


class OllamaLLMProvider:
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30,
        temperature: float = 0.1,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self._client = client

    async def health(self) -> LLMHealth:
        try:
            models = await self._installed_models()
        except LLMUnavailableError:
            return LLMHealth(status=LLMHealthStatus.UNAVAILABLE, provider=self.provider_name, model=self.model)

        if self.model not in models:
            return LLMHealth(
                status=LLMHealthStatus.MODEL_NOT_INSTALLED,
                provider=self.provider_name,
                model=self.model,
            )
        return LLMHealth(status=LLMHealthStatus.READY, provider=self.provider_name, model=self.model)

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
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise LLMInvalidJSONError("Ollama response did not include JSON text.")

        try:
            decoded = json.loads(raw_output)
            return AIOutput.model_validate(decoded)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMInvalidJSONError("Ollama response did not match AIOutput JSON contract.") from exc

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
        async with self._client_context() as client:
            response = await client.get(path)
            response.raise_for_status()
            return response.json()

    async def _post(self, path: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        async with self._client_context() as client:
            response = await client.post(path, json=json_payload)
            response.raise_for_status()
            return response.json()

    def _client_context(self) -> httpx.AsyncClient:
        if self._client is not None:
            return _BorrowedAsyncClient(self._client)
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)


class _BorrowedAsyncClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self.client

    async def __aexit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        return None
