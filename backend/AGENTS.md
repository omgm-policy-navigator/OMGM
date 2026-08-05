# Backend AGENTS.md

## Scope

`backend/` is the FastAPI modular monolith for OMGM MVP. It owns HTTP/SSE boundaries, conversation orchestration, question collection, policy lookup, deterministic eligibility evaluation, RAG coordination, graph projection, saved policies, notifications, anonymous session facts, and evaluation records.

The package root is `backend/src/app`. The Phase B0 folder contract maps to this import layout:

- `app/api`: FastAPI routers, request/response schemas, SSE boundaries, and safe error responses.
- `app/core`: configuration, logging, lifespan, and shared application errors.
- `app/db`: database session setup, migrations integration, and persistence helpers when DB work begins.
- `app/modules`: business modules grouped by feature responsibility. `app/modules/eligibility` owns the Rule Engine and evaluation domain logic.
- `app/llm`: AI output schemas, Ollama client wrappers, and prompt-facing DTOs. It must not calculate eligibility.

## Dependency Rules

- Routers may call module functions or services, but must not contain SQL or eligibility rules.
- Analysis modules must not depend on FastAPI routers or SQLAlchemy sessions.
- API response schemas and persistence entities must remain separate types.
- Rule Engine uses structured policy rules and user facts only.
- RAG retrieves approved evidence for policies already selected or evaluated by structured policy metadata and the Rule Engine. It does not create policy eligibility candidates.
- LLM code may normalize language, assist extraction, adjust search queries, and draft explanations. It must not create final eligibility status.
- LLM outputs must preserve the `app.llm.AIOutput` contract and use fallback statuses instead of inventing unsupported facts.
- Graph projection derives display relationships from stored policy and evaluation data. It does not own policy source data.
- Data pipeline code must not be imported into request handling.

## Data Ownership

- Anonymous sessions are server-generated cookie identities and own temporary conversation state until account identity exists.
- User fact modules own normalized answers, fact versions, and conflict markers.
- Data Pipeline owns raw API payloads, raw HTML/PDF, extraction candidates, review-pending data, and source hashes before publication.
- Backend Policy modules own approved and published `policy`, `policy_version`, `policy_rule`, `policy_document`, and service read models.
- Evaluation records are owned by eligibility modules and reference `policy_version` plus user fact version.

## Development Rules

- Keep Phase changes scoped. Do not add placeholder classes or future feature folders without a concrete contract.
- Validate inputs at API boundaries and return structured error responses.
- Do not log secrets, tokens, passwords, personal income/asset values, or raw sensitive user facts.
- Missing data remains unknown. Do not coerce nulls to false or zero.
- AI contract changes require schema tests and updates to `docs/architecture/ai-contracts.md`.
- Update `docs/architecture/api-contracts.md` when HTTP contracts change.
- Update `docs/architecture/backend.md` when backend module ownership changes.

## Verification

Backend changes should run the applicable local checks:

```bash
cd backend
python -m unittest discover -s tests
```

Repository-level checks should also include:

```bash
docker compose -f compose.yaml config
git diff --check
```

Run Alembic, pytest, and Ruff only after those tools are configured for the backend environment.
