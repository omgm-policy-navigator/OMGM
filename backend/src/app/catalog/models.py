from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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


class PolicyRelation(Base):
    __tablename__ = "policy_relation"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_policy_id: Mapped[str] = mapped_column(ForeignKey("policy.id"), nullable=False, index=True)
    target_policy_id: Mapped[str] = mapped_column(ForeignKey("policy.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)