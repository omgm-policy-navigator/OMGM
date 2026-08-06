"""Add anonymous sessions and user facts.

Revision ID: 20260806_0003
Revises: 20260805_0002
Create Date: 2026-08-06 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260806_0003"
down_revision: str | None = "20260805_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "anonymous_session",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_anonymous_session_token_hash", "anonymous_session", ["token_hash"])
    op.create_index("ix_anonymous_session_expires_at", "anonymous_session", ["expires_at"])
    op.create_index("ix_anonymous_session_idle_expires_at", "anonymous_session", ["idle_expires_at"])

    op.create_table(
        "user_fact",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("anonymous_session.id", ondelete="CASCADE"), nullable=False),
        sa.Column("condition_key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="manual"),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("session_id", "condition_key", name="uq_user_fact_session_condition"),
    )
    op.create_index("ix_user_fact_session_id", "user_fact", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_user_fact_session_id", table_name="user_fact")
    op.drop_table("user_fact")
    op.drop_index("ix_anonymous_session_idle_expires_at", table_name="anonymous_session")
    op.drop_index("ix_anonymous_session_expires_at", table_name="anonymous_session")
    op.drop_index("ix_anonymous_session_token_hash", table_name="anonymous_session")
    op.drop_table("anonymous_session")
