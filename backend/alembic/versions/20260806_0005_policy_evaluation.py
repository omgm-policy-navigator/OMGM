"""Add policy evaluation storage.

Revision ID: 20260806_0005
Revises: 20260806_0004
Create Date: 2026-08-06 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260806_0005"
down_revision: str | None = "20260806_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_evaluation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("anonymous_session.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("policy_id", sa.String(length=80), sa.ForeignKey("policy.id"), nullable=False),
        sa.Column("eligibility_status", sa.String(length=50), nullable=False),
        sa.Column("evaluation_state", sa.String(length=30), nullable=False),
        sa.Column("recommendation_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("fact_snapshot", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "policy_id", name="uq_policy_evaluation_session_policy"),
    )
    op.create_index("ix_policy_evaluation_session_id", "policy_evaluation", ["session_id"])
    op.create_index("ix_policy_evaluation_policy_id", "policy_evaluation", ["policy_id"])
    op.create_index("ix_policy_evaluation_state", "policy_evaluation", ["evaluation_state"])


def downgrade() -> None:
    op.drop_index("ix_policy_evaluation_state", table_name="policy_evaluation")
    op.drop_index("ix_policy_evaluation_policy_id", table_name="policy_evaluation")
    op.drop_index("ix_policy_evaluation_session_id", table_name="policy_evaluation")
    op.drop_table("policy_evaluation")