# AI Phase A1 Plan

## Goal

Call the local Ollama generation runtime reliably while keeping the backend resilient when the model or runtime is unavailable.

## Scope

- Define an LLM provider protocol and request/health contracts.
- Add an Ollama provider for `qwen3:4b` generation.
- Use non-thinking JSON generation mode with low temperature defaults.
- Add timeout and provider-specific failure mapping.
- Detect missing Ollama models through health checks and generation errors.
- Add fake and template providers for deterministic tests and local fallback.

## Out of Scope

- Backend AI API routes.
- RAG retrieval.
- Prompt templates for policy-specific explanations.
- Eligibility decisions or policy fact creation by the LLM.
