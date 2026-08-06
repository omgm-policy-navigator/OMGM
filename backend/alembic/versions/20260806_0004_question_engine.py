"""Add selected category to anonymous sessions.

Revision ID: 20260806_0004
Revises: 20260806_0003
Create Date: 2026-08-06 11:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260806_0004"
down_revision: str | None = "20260806_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("anonymous_session", sa.Column("selected_category_code", sa.String(length=50), nullable=True))
    op.create_foreign_key(
        "fk_anonymous_session_selected_category_code_category",
        "anonymous_session",
        "category",
        ["selected_category_code"],
        ["code"],
    )
    op.create_index(
        "ix_anonymous_session_selected_category_code",
        "anonymous_session",
        ["selected_category_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_anonymous_session_selected_category_code", table_name="anonymous_session")
    op.drop_constraint(
        "fk_anonymous_session_selected_category_code_category",
        "anonymous_session",
        type_="foreignkey",
    )
    op.drop_column("anonymous_session", "selected_category_code")
