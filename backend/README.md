# Backend

FastAPI modular monolith for the OMGM MVP. The package root is `backend/src/app`.

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

Health and readiness:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
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
- `app/modules`: feature module boundaries. `app/modules/eligibility` owns the Rule Engine.
- `app/llm`: Ollama/LLM boundary helpers.

See [Backend Architecture](../docs/architecture/backend.md) and [API Contracts](../docs/architecture/api-contracts.md) for detailed ownership and HTTP contracts.
