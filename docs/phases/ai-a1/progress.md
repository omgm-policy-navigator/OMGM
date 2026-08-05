# AI Phase A1 Progress

## Status

Implemented on branch `ai-a1-local-llm-runtime`.

## Completed Work

- Added `LLMProvider`, `LLMRequest`, and `LLMHealth` contracts.
- Added provider failure types for unavailable runtime, missing model, timeout, and invalid JSON output.
- Added `OllamaLLMProvider` using `/api/tags` for health and `/api/generate` for JSON generation.
- Configured Ollama generation with `stream=false`, `format=json`, `think=false`, `temperature=0.1`, and `timeout=30` defaults.
- Added `FakeLLMProvider` for deterministic replacement in tests.
- Added `TemplateLLMProvider` returning the safe `LLM_UNAVAILABLE` fallback without inventing policy facts.
- Added provider factory selection through `LLM_PROVIDER`.
- Added health-based fallback selection through `create_available_llm_provider`.
- Added robust JSON extraction for pure JSON, fenced JSON, and text-wrapped JSON responses.
- Added `RobustLLMManager` with fallback metadata and a static safety-net response when both primary and fallback providers fail.
- Added runtime-checkable provider protocol health compatibility through `check_health`.
- Added tests for provider swapping, health states, model missing handling, timeout handling, connection failure handling, and JSON contract validation.

## Deferred

- Prompt composition for concrete policy explanation workflows.
- RAG-backed context assembly.
- API routes that expose AI responses to frontend clients.
