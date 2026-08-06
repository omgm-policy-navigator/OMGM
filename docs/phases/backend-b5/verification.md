# Backend Phase B5 Verification

## Local Backend Checks

```bash
cd backend
uv run pytest tests\unit\test_eligibility.py tests\integration\test_session_evaluations_api.py
```

Result: passed. 23 tests passed.

```bash
cd backend
uv run pytest
```

Result: passed. 152 tests passed after merging latest `origin/main` and review hardening changes.

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

Result: blocked locally because Docker Desktop/Linux engine was not running.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
```

Result: blocked by the same Docker engine issue.

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

The blocker is recorded in `docs/troubleshooting/docker-backend-image.md`. Local `uv` checks passed for backend code and tests.