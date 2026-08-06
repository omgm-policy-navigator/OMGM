# Backend Architecture

## Phase B0 Decision

The backend is a single FastAPI modular monolith. It is not split into separate services for Rule Engine, RAG, LLM, graph projection, or policy APIs during the MVP.

The Python package root remains `backend/src/app` so local packaging and the existing Dockerfile continue to work. The requested B0 folder contract is represented under that package root:

```text
backend/
????? src/
??  ????? app/
??      ????? api/
??      ????? core/
??      ????? db/
??      ????? modules/
??      ??  ????? eligibility/
??      ????? llm/
????? tests/
    ????? unit/
    ????? integration/
    ????? fixtures/
```

`app/modules/eligibility` is the first concrete feature module. It owns the evaluation use case boundary and keeps Rule Engine logic as pure domain code inside the module. Future feature modules are created only when implementation begins.

## Responsibility Map

| Responsibility | Owner | May depend on | Must not do |
| --- | --- | --- | --- |
| HTTP and SSE boundary | `app/api` | `app/core`, feature modules | Write SQL, calculate eligibility rules, call Ollama directly from route handlers |
| Configuration, logging, lifespan, app errors | `app/core` | Python stdlib, framework primitives | Own business rules or persistence models |
| Database sessions and persistence setup | `app/db` | SQLAlchemy/Alembic when introduced, `app/core` config | Expose SQLAlchemy sessions to analysis modules as a required dependency |
| Rule Engine and eligibility evaluation | `app/modules/eligibility` | Structured policy rules, normalized user facts | Use LLM text to decide final status, generate natural-language explanations |
| Business features | `app/modules` | `app/core`, `app/db` repositories, sibling modules through explicit module functions, `app/llm` | Create broad layered folders without real implementation |
| LLM/Ollama boundary | `app/llm` | `app/core` config, AI output schemas, HTTP client library when introduced | Decide eligibility, persist raw sensitive facts, bypass policy evidence |
| RAG | `app/modules/rag` processing; retrieval deferred | approved documents and pure processing DTOs | Create policy eligibility candidates, invent policies, make final eligibility decisions, or access SQLAlchemy from processing code |
| Graph projection | Future `app/modules/graph` | policy metadata, relationships, evaluation summaries | Own source policy data or mutate eligibility results |

## Backend Feature Mapping

| Feature | Planned module owner | Contract status |
| --- | --- | --- |
| Health check | `app/api/health.py` | Implemented |
| Error response handling | `app/core/errors.py`, `app/main.py` | Implemented minimum, documented in API contracts |
| Anonymous session and user facts | `app/modules/sessions` | Implemented in B3 |
| Conversation orchestration | Future `app/modules/conversation` | Mock API contract only |
| Question engine | `app/modules/questions` | Implemented in B4 |
| User fact extraction | `app/modules/user_facts` | A2 extraction and conflict review implemented; API and persistence deferred |
| Policy catalog and detail lookup | Future `app/modules/policies` | Mock API contract only |
| Eligibility evaluation | `app/modules/eligibility` | Rule core implemented, API contract only |
| AI output contract | `app/llm` | Pydantic schema implemented, behavior contract documented |
| RAG document processing | `app/modules/rag` | D4 chunking, quality review, and embedding seed implemented |
| RAG evidence retrieval | Future `app/modules/rag` | Mock API contract only |
| Policy graph projection | Future `app/modules/graph` | Mock API contract only |
| Saved policies | Future `app/modules/saved_policies` | Deferred until retention and identity rules are decided |
| Notifications | Future `app/modules/notifications` | Deferred until channel, permission, and retention rules are decided |

## Database Access Rules

1. API routers receive HTTP requests, validate boundary inputs, and call module-level functions or services.
2. Routers do not write SQL and do not receive raw SQLAlchemy sessions as a business API.
3. Persistence code belongs behind repository-like functions in the owning module or shared `app/db` helpers once SQLAlchemy is introduced.
4. API response schemas are explicit DTOs. They are not SQLAlchemy entities.
5. Analysis modules accept plain Python data structures or typed DTOs, not FastAPI `Request` objects or SQLAlchemy `Session` objects.
6. Policy candidates are selected through policy metadata and structured rules. RAG can read approved document chunks and vector search results for already selected or evaluated policies, but it cannot create candidates or write final evaluation status.
7. Null, absent, or unverified facts are represented as unknown and excluded from deterministic calculation coverage.

## Ownership Boundaries

Anonymous sessions are server-generated and transported only through HttpOnly, Secure, SameSite cookies. The frontend must not read, create, or submit session IDs in JSON bodies.

User fact modules own normalized answers, source, confirmation state, fact version, and conflict state. The Data Pipeline owns raw API payloads, raw HTML/PDF, extraction candidates, review-pending data, and source hashes before publication. Backend Policy modules own approved and published `policy`, `policy_version`, `policy_rule`, `policy_document`, and service read models.

Eligibility owns evaluation records that reference immutable `policy_version` rows and user fact versions. The MVP uses an explicit `policy_version` concept from the start so stale evaluations can be detected without treating `verified_at` or source hashes as ad hoc versions.

The frontend owns browser display state only. It does not own policy source data, user fact normalization, eligibility decisions, RAG evidence, or graph projection logic.

## Test and Documentation Standards

Backend tests are grouped as:

- `backend/tests/unit`: pure functions, config, errors, Rule Engine, and module logic.
- `backend/tests/integration`: FastAPI app/API contracts, DB integration, migrations, and external boundary fakes.
- `backend/tests/fixtures`: non-sensitive samples only.

Any API contract change must update `docs/architecture/api-contracts.md` in the same PR. Any backend ownership change must update this document and `docs/architecture/module-boundaries.md` if repository-level boundaries change.

## Phase B1 Database Baseline

Phase B1 introduces SQLAlchemy async engine setup in `app/db/session.py`, Alembic migration wiring, and a database-backed readiness endpoint. No persistence entities are introduced in this phase; the initial migration enables the pgvector `vector` extension so future schema phases can build on a verified migration path.

`GET /health/live` is the process liveness check. `GET /health/ready` performs a PostgreSQL `select 1` through the configured async engine and returns `503` without raw database error details when the connection is unavailable. `GET /health` and `GET /ready` remain compatibility aliases.


## Phase A1 LLM Runtime

Phase A1 adds provider-swappable LLM runtime code under `app/llm`. `OllamaLLMProvider` owns local Ollama health checks, timeout handling, model-missing detection, non-thinking JSON generation, and `AIOutput` validation. `FakeLLMProvider` and `TemplateLLMProvider` allow tests and local fallback paths to avoid a live model.

The LLM runtime is not wired into API routes in A1. Connection failures, timeouts, missing models, and invalid JSON are represented as provider errors or health statuses so they do not become backend process health failures.

## Phase A2 User Fact Extraction

`app/modules/user_facts` owns the pure extraction contract: constrained prompt construction, seven-key allowlist validation, evidence grounding against user text, confidence and ambiguity review, and conflict detection against confirmed existing-fact DTOs. Duplicate confirmed facts are rejected at this boundary. It depends on the LLM request DTO but not on FastAPI, SQLAlchemy models, or sessions.

A2 does not persist candidates or expose an API. Candidate values remain explicitly marked as raw and requiring normalization. A later user-fact phase must normalize values and confirm ungrounded, ambiguous, low-confidence, or conflicting candidates before storage.

## Phase B3 Anonymous Sessions

Phase B3 adds `app/modules/sessions` for temporary anonymous identity and user facts. Session tokens are generated by the backend, sent only through the `anonymous_session` HttpOnly cookie, and stored in PostgreSQL only as SHA-256 hashes. `anonymous_session` owns temporary `user_fact` rows through `ON DELETE CASCADE`.

The module exposes cookie lifecycle endpoints and fact list/upsert endpoints under `/api/session`. Router code handles HTTP cookies and DTO mapping; repository functions own SQLAlchemy persistence. Missing or expired sessions return `SESSION_NOT_FOUND` instead of accepting client-provided IDs.

## Phase B4 Question Engine

Phase B4 adds `app/modules/questions` for deterministic question selection. The module owns MVP question templates, priority ordering, parent-child visibility through `showCondition`, DAG validation, answered-question exclusion, completion progress, conflict detection support, and DFS-based descendant fact invalidation guidance. It uses plain facts and category codes as input and does not depend on FastAPI routers or SQLAlchemy sessions.

The session API stores the selected category on `anonymous_session` and stores submitted answers as session-scoped `user_fact` rows. B4 does not evaluate policy eligibility or mark evaluations `STALE` because evaluation persistence is not implemented yet.
## Phase B5 Rule Engine and Evaluations

Phase B5 extends `app/modules/eligibility` with deterministic Rule Engine operators, required and optional conditions, limited OR groups, application-window status handling, recommendation scoring, and JSON evidence generation. The Rule Engine stays pure Python and does not depend on FastAPI routers or SQLAlchemy sessions.

The session API persists `policy_evaluation` rows scoped by anonymous session and policy. User fact changes mark existing current-session evaluations `STALE` so stale diagnostic results are not silently reused.
