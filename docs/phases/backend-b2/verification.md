# Backend Phase B2 Verification

## Local Backend Checks

```bash
cd backend
uv run pytest
```

Result: passed. 64 tests passed.

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

Result: passed. Migration `20260805_0002_policy_catalog` applied.

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec -T postgres psql -U marry_policy -d marry_policy -c "select (select count(*) from category) as categories, (select count(*) from policy where status='APPROVED' and is_active is true) as approved_active, (select count(*) from policy where is_active is false) as inactive;"
```

Result: passed.

```text
 categories | approved_active | inactive
------------+-----------------+----------
          5 |              12 |        1
```

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic downgrade -1
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
```

Result: passed. Down and up migration paths both completed.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
```

Result: passed. 64 tests passed in the Linux backend container.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
```

Result: passed.

```bash
python scripts/check-doc-links.py
git diff --check
```

Result: passed.

## Notes

- Migration adds policy catalog tables and seed data.
- Seed inserts use `ON CONFLICT` so rerunning seed SQL updates existing rows instead of duplicating them.
- B2 does not add policy evaluation, RAG chunking, or admin editing flows.