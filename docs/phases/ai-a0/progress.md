# AI Phase A0 Progress

## Status

Completed on branch `ai-phase-a0`.

## Completed Work

- Added `app.llm.AIOutput` and supporting Pydantic schemas.
- Defined AI result statuses for answered, needs-confirmation, insufficient-evidence, unavailable, and safety-blocked outputs.
- Documented allowed and forbidden AI responsibilities.
- Documented Rule Engine, RAG, and LLM ownership boundaries.
- Documented fallback contracts for LLM failure, insufficient evidence, and missing user facts.
- Added schema contract tests for alias serialization, null `nextQuestion`, unknown fields, and invalid result statuses.

## Deferred

- Ollama client implementation.
- Prompt and parsing implementation.
- AI API routes.
- RAG retrieval implementation.
