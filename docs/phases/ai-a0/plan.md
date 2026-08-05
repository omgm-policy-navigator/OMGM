# AI Phase A0 Plan

## Goal

Define the LLM role and output contract before implementing AI behavior.

## Scope

- Define AI output Pydantic schema.
- Document Rule, RAG, and LLM responsibility boundaries.
- Define fallback contracts for LLM failure, insufficient RAG evidence, and missing user facts.

## Completion Criteria

- AI output Pydantic schema exists.
- Rule, RAG, and LLM responsibility boundaries are documented.
- Failure fallback contract is documented.
- Phase A0 goal, implementation scope, and completion criteria are recorded in this phase folder.

## Out of Scope

- Calling Ollama.
- Prompt templates.
- RAG retrieval implementation.
- Policy rule extraction pipeline implementation.
- API routes for AI responses.
- Analysis D0 raw policy schemas, source classification, raw artifact storage conventions, processing/review/freshness status axes, and privacy collection gates.
