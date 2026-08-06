# Backend

FastAPI modular monolith for the OMGM MVP. The package root is `backend/src/app`.

Reviewed MVP policy data is versioned under `data/policy-seed`. The backend validates and loads it read-only at startup. Override the location with `POLICY_SEED_DIR` when necessary.

## Local Setup

```bash
cd backend
uv sync
```

Run migrations against the configured PostgreSQL database:

```bash
uv run alembic upgrade head
```

Run the API locally:

```bash
uv run uvicorn app.main:app --reload
```

After PostgreSQL migration and `qwen3-embedding:0.6b` installation in Ollama, reindex approved active RAG chunks:

```bash
uv run python -m app.modules.rag.reindex
```

Health and readiness:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

API docs are available at `http://localhost:8000/docs` while the server is running.

## Operations and security

Requests are limited to 64 KiB and 60 requests per client IP per 60 seconds by default. Override these with
`REQUEST_MAX_BODY_BYTES`, `RATE_LIMIT_REQUESTS`, and `RATE_LIMIT_WINDOW_SECONDS`. Anonymous sessions are removed every
`SESSION_CLEANUP_INTERVAL_SECONDS` and can also be cleaned explicitly after setting `ADMIN_API_KEY`:

```bash
curl -X POST http://localhost:8000/api/v1/admin/sessions/cleanup \
  -H "Authorization: Bearer ${ADMIN_API_KEY}"
```

Do not place the admin key in browser code or a `VITE_*` variable. Ollama calls use `LLM_TIMEOUT_SECONDS` and retry
transient timeout/network/502/503/504 failures up to `LLM_MAX_ATTEMPTS`.

The body limit counts actual received bytes, including chunked requests. Behind a reverse proxy, set
`TRUSTED_PROXY_IPS` only to direct proxy IPs under your control; forwarded client IP headers from other peers are
ignored. A gateway-level body and rate limit should also be configured for production.

## Verification

```bash
uv run pytest
uv run ruff check src/app tests
uv run alembic downgrade base
uv run alembic upgrade head
```

## Structure

- `app/api`: FastAPI routers, REST/SSE boundaries, and safe error responses.
- `app/core`: configuration, logging, lifespan, and common errors.
- `app/db`: SQLAlchemy async engine/session setup and Alembic integration.
- `app/modules`: feature module boundaries. `eligibility` owns the Rule Engine and `rag` owns embedding/indexing and policy-scoped retrieval.
- `app/modules/policies`: read-only policy CSV validation and catalog access.
- `app/llm`: AI response schemas and Ollama/LLM boundary helpers.
- `data/policy-seed`: reviewed policy, question, rule, relation, and RAG document CSVs.

See [Backend Architecture](../docs/architecture/backend.md), [API Contracts](../docs/architecture/api-contracts.md), and [AI Contracts](../docs/architecture/ai-contracts.md) for detailed ownership and HTTP/AI contracts.
