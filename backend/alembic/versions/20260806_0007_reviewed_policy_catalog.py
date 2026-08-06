"""Load reviewed policy catalog URLs.

Revision ID: 20260806_0007
Revises: 20260806_0006
Create Date: 2026-08-06 15:40:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects.postgresql import insert

from app.catalog.models import Category, Policy, PolicyDocument, PolicyRelation, PolicyRule, Question
from app.core.config import AppConfig
from app.db.seed import question_rows, reviewed_seed_payload, rule_rows
from app.modules.policies import load_policy_seed

revision: str = "20260806_0007"
down_revision: str | Sequence[str] | None = "20260806_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    catalog = load_policy_seed(AppConfig.from_env().policy_seed_dir)
    categories, policies, documents, relations, _policy_id_map = reviewed_seed_payload(catalog)
    connection = op.get_bind()

    _upsert_rows(connection, Category, categories, ["code"])
    _upsert_rows(connection, Policy, policies, ["id"])
    _upsert_rows(connection, Question, question_rows(policies), ["id"])
    _upsert_rows(connection, PolicyRule, rule_rows(policies), ["id"])
    _upsert_rows(connection, PolicyDocument, documents, ["id"])
    _upsert_rows(connection, PolicyRelation, relations, ["id"])


def downgrade() -> None:
    pass


def _upsert_rows(connection, model, rows: list[dict], conflict_keys: list[str]) -> None:
    for row in rows:
        statement = insert(model).values(**row)
        update_values = {key: statement.excluded[key] for key in row if key not in conflict_keys}
        statement = statement.on_conflict_do_update(index_elements=conflict_keys, set_=update_values)
        connection.execute(statement)
