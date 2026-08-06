# Backend Phase B6 Verification

## Local Backend Checks

```bash
cd backend
uv run pytest tests\unit\test_graph_projection.py tests\integration\test_session_graph_api.py
```

Result: passed. 9 tests passed.

```bash
cd backend
uv run pytest
```

Result: passed. 161 tests passed after graph hardening changes.

```bash
cd backend
uv run ruff check src/app tests
```

Result: passed.

## Docker Checks

```bash
docker compose -f compose.yaml -f compose.dev.yaml config
```

Result: passed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
```

Result: blocked locally because Docker Desktop/Linux engine was not running. B6 adds no Alembic migration.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
```

Result: blocked by the same Docker engine issue.

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

The blocker is documented in `docs/troubleshooting/docker-backend-image.md`. Local `uv` checks passed for backend code and tests.