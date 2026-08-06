# Backend Phase B8 Verification

## Commands

- `docker compose -f compose.yaml -f compose.dev.yaml config` - passed.
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head` - passed from an empty database through `20260806_0008`.
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest` - passed, 229 tests.
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests` - passed.
- Local pytest with a repository-owned `--basetemp` - passed, 228 tests and 1 skipped because pgvector integration is container-only.
- `git diff --check` - passed before final commit.

The first container migration run exposed a historical-migration compatibility issue caused by a Python-side ORM
default. Moving the new approval default to the database server default resolved it; a clean migration and the
pgvector integration test then passed.

## Migration

`20260806_0008_operations_security.py` adds indexed non-null `approval_status` columns to `policy_rule` and
`policy_document`. Existing reviewed rows are backfilled as `APPROVED`; newly inserted rows default to `DRAFT`.
