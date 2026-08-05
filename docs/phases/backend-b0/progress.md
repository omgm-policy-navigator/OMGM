# Backend Phase B0 Progress

## Status

Completed on branch `backend-phase-b0`.

## Completed Work

- Confirmed backend remains a FastAPI modular monolith.
- Mapped B0 package contract to existing `backend/src/app` layout.
- Added backend-local agent instructions for module ownership and dependency rules.
- Added `app/db`, `app/llm`, and `app/modules` package boundaries.
- Reorganized backend tests into `unit`, `integration`, and `fixtures` folders.
- Documented API draft, cookie-based anonymous session contract, error response contract, separated eligibility/evaluation statuses, and mock rules.
- Documented backend database access rules and feature-to-module ownership.
- Clarified that RAG retrieves approved evidence for structured candidates and does not create policy eligibility candidates.
- Confirmed MVP policy versioning uses explicit `policy_version` ownership rather than `verified_at` or source hashes as ad hoc versions.

## Deferred

- SQLAlchemy and Alembic implementation is deferred because no models or migrations exist yet. The policy versioning contract is documented for the implementation phase.
- Ruff configuration is deferred unless the backend adopts Ruff in a later phase.
- Concrete RAG, LLM, graph, and session modules are deferred until implementation phases.
- Saved policy and notification API contracts are deferred until identity, retention, channel, and browser permission rules are decided.
