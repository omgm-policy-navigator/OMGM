import json
import unittest
from unittest.mock import patch

import httpx

from app.core.config import AppConfig
from app.llm import (
    AIOutput,
    AIResultStatus,
    FakeLLMProvider,
    LLMHealth,
    LLMHealthStatus,
    LLMInvalidJSONError,
    LLMModelNotInstalledError,
    LLMProvider,
    LLMRequest,
    LLMTimeoutError,
    LLMUnavailableError,
    OllamaLLMProvider,
    TemplateLLMProvider,
    create_available_llm_provider,
    create_llm_provider,
    parse_ai_output_json,
)

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


def answered_output() -> dict[str, object]:
    return {
        "answer": "The condition is supported by the cited notice.",
        "resultStatus": "ANSWERED",
        "matchedConditions": [],
        "missingConditions": [],
        "citations": [
            {
                "sourceId": "doc_1",
                "title": "Notice",
                "url": "https://example.go.kr/policy/1",
                "policyVersionId": "policy_version_1",
                "evidenceId": "chunk_1",
            }
        ],
        "nextQuestion": None,
    }


def async_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.test")


class LLMProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_fake_provider_returns_configured_ai_output(self) -> None:
        output = AIOutput.model_validate(answered_output())
        provider = FakeLLMProvider(output=output)

        result = await provider.generate(LLMRequest(prompt="Explain this policy."))
        health = await provider.health()

        self.assertIsInstance(provider, LLMProvider)
        self.assertTrue(await provider.check_health())
        self.assertEqual(result.result_status, AIResultStatus.ANSWERED)
        self.assertEqual(provider.requests[0].prompt, "Explain this policy.")
        self.assertEqual(health.status, LLMHealthStatus.READY)

    async def test_template_provider_returns_safe_unavailable_fallback(self) -> None:
        provider = TemplateLLMProvider()

        result = await provider.generate(LLMRequest(prompt="Explain this policy."))

        self.assertIsInstance(provider, LLMProvider)
        self.assertTrue(await provider.check_health())
        self.assertEqual(result.result_status, AIResultStatus.LLM_UNAVAILABLE)
        self.assertEqual(result.citations, [])

    async def test_ollama_health_ready_when_model_is_installed(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}]})

        async with async_client(handler) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            health = await provider.health()

        self.assertIsInstance(provider, LLMProvider)
        self.assertEqual(health.status, LLMHealthStatus.READY)

    async def test_ollama_default_client_uses_strict_timeout(self) -> None:
        provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", timeout_seconds=30)
        try:
            self.assertEqual(provider._client.timeout.connect, 30)
            self.assertEqual(provider._client.timeout.read, 30)
            self.assertEqual(provider._client.timeout.write, 30)
            self.assertEqual(provider._client.timeout.pool, 30)
        finally:
            await provider.aclose()

    async def test_ollama_health_reports_missing_model_without_raising(self) -> None:
        async with async_client(lambda _request: httpx.Response(200, json={"models": [{"name": "other"}]})) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            health = await provider.health()
            ready = await provider.check_health()

        self.assertFalse(ready)
        self.assertEqual(health.status, LLMHealthStatus.MODEL_NOT_INSTALLED)

    async def test_ollama_health_reports_connection_failure_without_raising(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        async with async_client(handler) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            health = await provider.health()

        self.assertEqual(health.status, LLMHealthStatus.UNAVAILABLE)

    async def test_ollama_generate_requests_non_thinking_json_mode(self) -> None:
        seen_payloads: list[dict[str, object]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            seen_payloads.append(payload)
            return httpx.Response(200, json={"response": json.dumps(answered_output())})

        async with async_client(handler) as client:
            provider = OllamaLLMProvider(
                "http://ollama.test",
                "qwen3:4b",
                timeout_seconds=30,
                temperature=0.1,
                client=client,
            )

            result = await provider.generate(LLMRequest(prompt="Return JSON.", system="Use the contract."))

        self.assertEqual(result.result_status, AIResultStatus.ANSWERED)
        self.assertEqual(seen_payloads[0]["model"], "qwen3:4b")
        self.assertEqual(seen_payloads[0]["format"], "json")
        self.assertEqual(seen_payloads[0]["stream"], False)
        self.assertEqual(seen_payloads[0]["think"], False)
        self.assertEqual(seen_payloads[0]["options"], {"temperature": 0.1})

    async def test_ollama_generate_extracts_json_from_wrapped_text(self) -> None:
        wrapped = "Here is the JSON:\n```json\n" + json.dumps(answered_output()) + "\n```"
        async with async_client(lambda _request: httpx.Response(200, json={"response": wrapped})) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            result = await provider.generate(LLMRequest(prompt="Return JSON."))

        self.assertEqual(result.result_status, AIResultStatus.ANSWERED)

    async def test_ollama_generate_maps_404_to_model_not_installed(self) -> None:
        async with async_client(lambda _request: httpx.Response(404, json={"error": "model not found"})) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            with self.assertRaises(LLMModelNotInstalledError):
                await provider.generate(LLMRequest(prompt="Return JSON."))

    async def test_ollama_generate_maps_timeout(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        async with async_client(handler) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            with self.assertRaises(LLMTimeoutError):
                await provider.generate(LLMRequest(prompt="Return JSON."))

    async def test_ollama_generate_rejects_invalid_json_contract(self) -> None:
        async with async_client(lambda _request: httpx.Response(200, json={"response": "not json"})) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            with self.assertRaises(LLMInvalidJSONError):
                await provider.generate(LLMRequest(prompt="Return JSON."))

    async def test_ollama_generate_maps_connection_failure(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        async with async_client(handler) as client:
            provider = OllamaLLMProvider("http://ollama.test", "qwen3:4b", client=client)

            with self.assertRaises(LLMUnavailableError):
                await provider.generate(LLMRequest(prompt="Return JSON."))

    async def test_parse_ai_output_json_rejects_invalid_wrapped_text(self) -> None:
        with self.assertRaises(LLMInvalidJSONError):
            parse_ai_output_json("Before {\"resultStatus\": \"ANSWERED\"} after")

    def test_factory_selects_configured_provider(self) -> None:
        fake = create_llm_provider(AppConfig(database_url=TEST_DATABASE_URL, llm_provider="fake"))
        template = create_llm_provider(AppConfig(database_url=TEST_DATABASE_URL, llm_provider="template"))
        ollama = create_llm_provider(AppConfig(database_url=TEST_DATABASE_URL, llm_provider="ollama"))

        self.assertIsInstance(fake, FakeLLMProvider)
        self.assertIsInstance(template, TemplateLLMProvider)
        self.assertIsInstance(ollama, OllamaLLMProvider)


class LLMAvailableFactoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_available_factory_keeps_fake_provider(self) -> None:
        provider = await create_available_llm_provider(AppConfig(database_url=TEST_DATABASE_URL, llm_provider="fake"))

        self.assertIsInstance(provider, FakeLLMProvider)

    async def test_available_factory_falls_back_when_model_is_missing(self) -> None:
        class MissingProvider:
            provider_name = "ollama"

            async def health(self) -> LLMHealth:
                return LLMHealth(
                    status=LLMHealthStatus.MODEL_NOT_INSTALLED,
                    provider="ollama",
                    model="qwen3:4b",
                )

            async def check_health(self) -> bool:
                return False

            async def generate(self, request: LLMRequest) -> AIOutput:
                raise AssertionError("fallback should replace the missing provider")

        config = AppConfig(database_url=TEST_DATABASE_URL, llm_provider="ollama")
        with patch("app.llm.factory.create_llm_provider", return_value=MissingProvider()):
            provider = await create_available_llm_provider(config)

        self.assertIsInstance(provider, TemplateLLMProvider)
