# Backend Phase B2 Progress

## Status

Implemented on branch `backend-b2-policy-catalog`.

## Completed Work

- Added catalog ORM models for categories, policies, questions, rules, documents, and policy relations.
- Added Alembic migration `20260805_0002_policy_catalog` with idempotent seed inserts.
- Added runtime seed command `python -m app.db.seed` using PostgreSQL upserts.
- Seed data includes five categories, twelve approved active policies, and one inactive draft policy used to verify exposure blocking.
- Added policy catalog API routes under `/api`.
- Added DTO schemas so API responses do not expose SQLAlchemy entities directly.
- Added tests for category listing, approved policy listing, inactive policy blocking, detail source fields, documents, and 404 handling.
- Added eager loading for policy detail/document relationship reads to avoid relationship-level N+1 queries.
- Added `PolicyStatus` enum and active policy filter helper so category, detail, and document queries all enforce approved active policy scope.

## Deferred

- Full policy version lifecycle.
- Policy evaluation against `policy_rule`.
- Document chunking and vector embeddings.