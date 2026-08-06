# Backend Phase B7 Verification

## Local Commands

- `uv run pytest tests/unit/test_ai_explanations.py` - passed, 3 tests.
- `uv run pytest tests/integration/test_ai_explanation_api.py` - passed, 3 tests.
- `uv run pytest tests/unit/test_ai_explanations.py tests/integration/test_ai_explanation_api.py` - passed, 6 tests after merging latest `main`.
- `uv run pytest` - passed, 178 tests and 1 skipped after merging latest `main`.
- `uv run ruff check src/app tests` - passed.
- `docker compose -f compose.yaml -f compose.dev.yaml config` - passed.
- `git diff --check` - passed before the merge update; rerun before final push.

## Docker-Based Commands

- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head` - blocked locally because Docker Desktop/Linux engine was not running.
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest` - blocked locally because Docker Desktop/Linux engine was not running before latest main merge.
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check app tests` - blocked locally because Docker Desktop/Linux engine was not running before latest main merge.

The Docker failure was: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.

## Migration

No B7-owned Alembic migration is required. After merging latest `main`, the branch includes the upstream RAG vector-index migration `20260806_0006_rag_vector_index.py`.
