# Backend Architecture

## Phase B0 Decision

The backend is a single FastAPI modular monolith. It is not split into separate services for Rule Engine, RAG, LLM, graph projection, or policy APIs during the MVP.

The Python package root remains `backend/src/app` so local packaging and the existing Dockerfile continue to work. The requested B0 folder contract is represented under that package root:

```text
backend/
├── src/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── db/
│       ├── modules/
│       │   └── eligibility/
│       └── llm/
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
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
| LLM/Ollama boundary | `app/llm` | `app/core` config, HTTP client library when introduced | Decide eligibility, persist raw sensitive facts, bypass policy evidence |
| RAG | Future `app/modules/rag` | approved document chunks for policies selected by metadata and Rule Engine, embeddings, metadata filters, `app/llm` query helpers | Create policy eligibility candidates, invent policies, or make final eligibility decisions |
| Graph projection | Future `app/modules/graph` | policy metadata, relationships, evaluation summaries | Own source policy data or mutate eligibility results |

## Backend Feature Mapping

| Feature | Planned module owner | Contract status |
| --- | --- | --- |
| Health check | `app/api/health.py` | Implemented |
| Error response handling | `app/core/errors.py`, `app/main.py` | Implemented minimum, documented in API contracts |
| Anonymous session | Future `app/modules/sessions` | Mock API contract only |
| Conversation orchestration | Future `app/modules/conversation` | Mock API contract only |
| Question engine and user facts | Future `app/modules/user_facts` | Mock API contract only |
| Policy catalog and detail lookup | Future `app/modules/policies` | Mock API contract only |
| Eligibility evaluation | `app/modules/eligibility` | Rule core implemented, API contract only |
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
