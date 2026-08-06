"""Add RAG chunks and pgvector embeddings.

Revision ID: 20260806_0006
Revises: 20260806_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


class Vector1024(sa.types.UserDefinedType):
    def get_col_spec(self, **kw: object) -> str:
        return "vector(1024)"

revision: str = "20260806_0006"
down_revision: str | None = "20260806_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_chunk",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("document_id", sa.String(length=100), nullable=False),
        sa.Column("policy_id", sa.String(length=80), nullable=False),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("policy_status", sa.String(length=30), nullable=False),
        sa.Column("document_status", sa.String(length=30), nullable=False),
        sa.Column("trust_level", sa.String(length=30), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("chunk_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_location", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "source_location", "content_hash", name="uq_document_chunk_source"),
    )
    op.create_index(
        "ix_document_chunk_policy_filters",
        "document_chunk",
        ["policy_id", "document_status", "trust_level", "policy_status"],
    )
    op.create_table(
        "document_chunk_embedding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "chunk_id",
            sa.String(length=100),
            sa.ForeignKey("document_chunk.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("embedding", Vector1024(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("chunk_id", "model", name="uq_chunk_embedding_model"),
    )
    op.execute(
        "CREATE INDEX ix_chunk_embedding_cosine ON document_chunk_embedding "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_embedding_cosine", table_name="document_chunk_embedding")
    op.drop_table("document_chunk_embedding")
    op.drop_index("ix_document_chunk_policy_filters", table_name="document_chunk")
    op.drop_table("document_chunk")
