# Backend Phase B1 Plan

## Goal

Initialize the FastAPI backend with PostgreSQL connectivity, Alembic migrations, Docker support, and CI verification.

## Scope

- Configure backend dependencies through `uv`.
- Add SQLAlchemy async engine/session setup.
- Add Alembic configuration and an initial empty baseline migration.
- Keep `/health` as process health and add `/ready` for PostgreSQL readiness.
- Add Docker/dev compose support for backend verification.
- Update Backend CI to run migrations, pytest, and Ruff.

## Out of Scope

- Application persistence models.
- Policy, session, conversation, RAG, graph, saved policy, or notification tables.
- Business repositories beyond shared DB connection setup.
