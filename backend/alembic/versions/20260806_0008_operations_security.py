"""operations and content approval security

Revision ID: 20260806_0008
Revises: 20260806_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0008"
down_revision: str | None = "20260806_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "policy_rule",
        sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="DRAFT"),
    )
    op.add_column(
        "policy_document",
        sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="DRAFT"),
    )
    op.create_index("ix_policy_rule_approval_status", "policy_rule", ["approval_status"])
    op.create_index("ix_policy_document_approval_status", "policy_document", ["approval_status"])
    # B7 overwrote these exact versioned reviewed-seed rows. Unrelated legacy rows remain DRAFT.
    op.execute(
        """
        UPDATE policy_rule AS rule
        SET approval_status = 'APPROVED'
        FROM policy AS policy
        WHERE rule.policy_id = policy.id
          AND rule.id = 'rule_' || policy.id || '_region'
          AND policy.status = 'APPROVED'
          AND policy.is_active IS TRUE
          AND policy.reviewed_at IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE policy_document AS document
        SET approval_status = 'APPROVED'
        FROM policy AS policy
        WHERE document.policy_id = policy.id
          AND document.id = 'doc_' || policy.id
          AND policy.status = 'APPROVED'
          AND policy.is_active IS TRUE
          AND policy.reviewed_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_policy_document_approval_status", table_name="policy_document")
    op.drop_index("ix_policy_rule_approval_status", table_name="policy_rule")
    op.drop_column("policy_document", "approval_status")
    op.drop_column("policy_rule", "approval_status")
