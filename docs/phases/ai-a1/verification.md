# AI Phase A1 Verification

## Commands Run

```bash
cd backend
uv sync
```

Result: passed. `httpx` was installed and `uv.lock` was updated.

```bash
cd backend
uv run pytest
```

Result: passed. 59 tests passed.

```bash
cd backend
uv run ruff check src/app tests
```

Result: passed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
```

Result: passed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml build backend
```

Result: passed. Backend image includes `httpx` for the Ollama provider.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
```

Result: passed. No new migrations were introduced in A1.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
```

Result: passed. 59 tests passed in the Linux backend container.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
```

Result: passed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend python -c "import asyncio, json; from app.core.config import AppConfig; from app.llm import create_llm_provider; health = asyncio.run(create_llm_provider(AppConfig.from_env()).health()); print(json.dumps({'status': str(health.status), 'provider': health.provider, 'model': health.model}))"
```

Result: passed. The local Ollama runtime responded without crashing the backend path; `qwen3:4b` was reported as `MODEL_NOT_INSTALLED` in this environment.

```bash
python scripts/check-doc-links.py
```

Result: passed.

```bash
git diff --check
```

Result: passed.

## Notes

- JSON output mode, text-wrapped JSON extraction, fallback metadata, and static safety-net fallback are validated with mocked provider responses because the local `qwen3:4b` model is not installed in this environment.
- A1 does not add API routes or database migrations.
