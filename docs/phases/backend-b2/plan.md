# Backend Phase B2 Plan

## Goal

Load and query policy categories, policies, questions, rules, documents, and policy relations from PostgreSQL.

## Scope

- Add catalog SQLAlchemy models for `category`, `policy`, `question`, `policy_rule`, `policy_document`, and `policy_relation`.
- Add Alembic migration with idempotent seed data for five categories and twelve approved policies.
- Add policy catalog read APIs:
  - `GET /api/categories`
  - `GET /api/categories/{code}/policies`
  - `GET /api/policies/{policy_id}`
  - `GET /api/policies/{policy_id}/documents`
- Block inactive or unapproved policies from public API responses.

## Out of Scope

- Policy evaluation and Rule Engine integration.
- RAG document chunking and embeddings.
- Admin editing flows.
- Frontend catalog UI.