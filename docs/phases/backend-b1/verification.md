# Backend Phase B1 Verification

## Commands Run

```bash
cd backend
uv sync
```

Result: passed. `uv.lock` was generated/updated.

```bash
cd backend
uv run pytest
```

Result: passed. 21 tests passed.

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
docker compose -f compose.yaml config --quiet
```

Result: passed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml build backend
```

Result: passed. Backend image includes runtime dependencies plus pytest/Ruff for container verification.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic downgrade base
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
```

Result: passed. Baseline migration `20260805_0001` enables the pgvector `vector` extension and upgrades/downgrades successfully against PostgreSQL.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
```

Result: passed. 21 tests passed in the Linux backend container.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
```

Result: passed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d backend
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health/live
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health/ready
```

Result: passed. `/health/live` returned `200` with `status: ok`; `/health/ready` returned `200` with `database: ok`.

```bash
git diff --check
```

Result: passed.

## Notes

- Local `uv run` commands require access to the user uv cache outside the repository on this Windows machine.
- The package path is `src/app`, so Ruff verification uses `ruff check src/app tests` rather than `ruff check app tests`.
