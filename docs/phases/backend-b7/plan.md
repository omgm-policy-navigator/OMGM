# Backend Phase B7 Plan

## Goal

Provide official-document-based AI explanations by combining deterministic Rule Engine results, approved RAG evidence, and LLM-generated plain-language text.

## Scope

- Add session-scoped chat and policy explanation APIs.
- Retrieve approved active policy documents as citation sources.
- Preserve Rule Engine `eligibilityStatus` as the authoritative decision.
- Validate structured API responses with Pydantic schemas.
- Provide SSE events for chat streaming.
- Return fallback responses when approved evidence or the LLM provider is unavailable.

## Out of Scope

- Changing policy eligibility decisions with LLM output.
- New graph, saved-policy, notification, or external policy collection features.
- Persisting chat conversation history.
- Adding a new vector or graph database.
