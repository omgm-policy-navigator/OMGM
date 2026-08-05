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
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend python -m app.db.seed
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend python -m app.db.seed
```

Result: passed. Runtime seed command completed twice without duplicate rows.

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
- `PolicyStatus` enum-backed filters enforce approved active policy scope for category, detail, and document reads.
- Seed inserts use `ON CONFLICT` so rerunning migration seed SQL or `python -m app.db.seed` updates existing rows instead of duplicating them.
- Public B2 routes intentionally remain under `/api/...` because `docs/architecture/api-contracts.md` defines MVP endpoints without a version prefix; `/api/v1` is deferred until a breaking version is introduced.
- B2 does not add policy evaluation, RAG chunking, or admin editing flows.