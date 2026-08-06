from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType


class Base(DeclarativeBase):
    pass


class Vector1024(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "vector(1024)"




class PolicyStatus(StrEnum):
    APPROVED = "APPROVED"
    DRAFT = "DRAFT"
    INACTIVE = "INACTIVE"

class Category(Base):
    __tablename__ = "category"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    policies: Mapped[list[Policy]] = relationship(back_populates="category")


class Policy(Base):
    __tablename__ = "policy"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    category_code: Mapped[str] = mapped_column(ForeignKey("category.code"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    agency: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    application_period: Mapped[str] = mapped_column(String(160), nullable=False)
    support_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    official_source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_label: Mapped[str] = mapped_column(String(160), nullable=False)
    reviewed_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[Category] = relationship(back_populates="policies")
    documents: Mapped[list[PolicyDocument]] = relationship(back_populates="policy")
    questions: Mapped[list[Question]] = relationship(back_populates="policy")
    rules: Mapped[list[PolicyRule]] = relationship(back_populates="policy")
    evaluations: Mapped[list[PolicyEvaluation]] = relationship(back_populates="policy")


class Question(Base):
    __tablename__ = "question"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("policy.id"), index=True)
    fact_key: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt: Mapped[str] = mapped_column(String(500), nullable=False)
    answer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    policy: Mapped[Policy | None] = relationship(back_populates="questions")


class PolicyRule(Base):
    __tablename__ = "policy_rule"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policy.id"), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value_text: Mapped[str] = mapped_column(String(200), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)

    policy: Mapped[Policy] = relationship(back_populates="rules")


class PolicyDocument(Base):
    __tablename__ = "policy_document"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policy.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    official_source: Mapped[str] = mapped_column(String(160), nullable=False)
    reviewed_at: Mapped[date] = mapped_column(Date, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(80), nullable=False)

    policy: Mapped[Policy] = relationship(back_populates="documents")


class DocumentChunk(Base):
    __tablename__ = "document_chunk"
    __table_args__ = (
        UniqueConstraint("document_id", "source_location", "content_hash", name="uq_document_chunk_source"),
        Index("ix_document_chunk_policy_filters", "policy_id", "document_status", "trust_level", "policy_status"),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(80), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_status: Mapped[str] = mapped_column(String(30), nullable=False)
    document_status: Mapped[str] = mapped_column(String(30), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(30), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_location: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DocumentChunkEmbedding(Base):
    __tablename__ = "document_chunk_embedding"
    __table_args__ = (UniqueConstraint("chunk_id", "model", name="uq_chunk_embedding_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("document_chunk.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector1024(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PolicyRelation(Base):
    __tablename__ = "policy_relation"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_policy_id: Mapped[str] = mapped_column(ForeignKey("policy.id"), nullable=False, index=True)
    target_policy_id: Mapped[str] = mapped_column(ForeignKey("policy.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)

class PolicyEvaluation(Base):
    __tablename__ = "policy_evaluation"
    __table_args__ = (
        UniqueConstraint("session_id", "policy_id", name="uq_policy_evaluation_session_policy"),
        Index("ix_policy_evaluation_session_id", "session_id"),
        Index("ix_policy_evaluation_policy_id", "policy_id"),
        Index("ix_policy_evaluation_state", "evaluation_state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("anonymous_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_id: Mapped[str] = mapped_column(ForeignKey("policy.id"), nullable=False)
    eligibility_status: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluation_state: Mapped[str] = mapped_column(String(30), nullable=False)
    recommendation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    fact_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    policy: Mapped[Policy] = relationship(back_populates="evaluations")
