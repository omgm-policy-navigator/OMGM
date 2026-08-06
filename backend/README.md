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
