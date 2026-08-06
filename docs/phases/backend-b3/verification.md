# Backend Phase B3 Verification

## Local Backend Checks

```bash
cd backend
uv run pytest tests\integration\test_anonymous_session_api.py
```

Result: passed. 10 tests passed.

```bash
cd backend
uv run pytest
```

Result: passed. 89 tests passed.

```bash
cd backend
uv run ruff check src/app tests
```

Result: passed.

```bash
python scripts\check-doc-links.py
```

Result: passed. Markdown links ok.

```bash
git diff --check
```

Result: passed. Git reported only CRLF normalization warnings for touched text files.

## Docker Checks

```bash
docker compose -f compose.yaml -f compose.dev.yaml config
```

Result: passed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
```

Result: blocked locally because Docker Desktop/Linux engine was not running.

```text
unable to get image 'ollama/ollama:latest': failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running
```

The same Docker daemon blocker prevented container `pytest` and `ruff` runs in this session. Local `uv` checks passed for the backend code and tests.