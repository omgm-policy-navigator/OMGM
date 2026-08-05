"""Add policy catalog tables and seed data.

Revision ID: 20260805_0002
Revises: 20260805_0001
Create Date: 2026-08-05 01:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260805_0002"
down_revision: str | None = "20260805_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "category",
        sa.Column("code", sa.String(length=50), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "policy",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("category_code", sa.String(length=50), sa.ForeignKey("category.code"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("agency", sa.String(length=160), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("application_period", sa.String(length=160), nullable=False),
        sa.Column("support_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("official_source_url", sa.String(length=500), nullable=False),
        sa.Column("source_label", sa.String(length=160), nullable=False),
        sa.Column("reviewed_at", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_policy_category_code", "policy", ["category_code"])
    op.create_index("ix_policy_status", "policy", ["status"])
    op.create_index("ix_policy_is_active", "policy", ["is_active"])
    op.create_table(
        "question",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("policy_id", sa.String(length=80), sa.ForeignKey("policy.id"), nullable=True),
        sa.Column("fact_key", sa.String(length=80), nullable=False),
        sa.Column("prompt", sa.String(length=500), nullable=False),
        sa.Column("answer_type", sa.String(length=50), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_question_policy_id", "question", ["policy_id"])
    op.create_table(
        "policy_rule",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("policy_id", sa.String(length=80), sa.ForeignKey("policy.id"), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("fact_key", sa.String(length=80), nullable=False),
        sa.Column("operator", sa.String(length=30), nullable=False),
        sa.Column("value_text", sa.String(length=200), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("evidence_text", sa.Text(), nullable=False),
    )
    op.create_index("ix_policy_rule_policy_id", "policy_rule", ["policy_id"])
    op.create_table(
        "policy_document",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("policy_id", sa.String(length=80), sa.ForeignKey("policy.id"), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("official_source", sa.String(length=160), nullable=False),
        sa.Column("reviewed_at", sa.Date(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_hash", sa.String(length=80), nullable=False),
    )
    op.create_index("ix_policy_document_policy_id", "policy_document", ["policy_id"])
    op.create_table(
        "policy_relation",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("source_policy_id", sa.String(length=80), sa.ForeignKey("policy.id"), nullable=False),
        sa.Column("target_policy_id", sa.String(length=80), sa.ForeignKey("policy.id"), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
    )
    op.create_index("ix_policy_relation_source_policy_id", "policy_relation", ["source_policy_id"])
    op.create_index("ix_policy_relation_target_policy_id", "policy_relation", ["target_policy_id"])

    seed_catalog()


def seed_catalog() -> None:
    op.execute(
        """
        INSERT INTO category (code, name, description, sort_order) VALUES
        ('housing', 'Housing', 'Housing and rent support', 10),
        ('loan', 'Loan', 'Marriage and household loan support', 20),
        ('cash', 'Cash Benefit', 'Direct allowance and grant support', 30),
        ('childcare', 'Childcare', 'Pregnancy and childcare support', 40),
        ('education', 'Education', 'Counseling and education programs', 50)
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            sort_order = EXCLUDED.sort_order;
        """
    )
    op.execute(
        """
        INSERT INTO policy (
            id, category_code, title, agency, region, summary, application_period, support_type, status, is_active,
            official_source_url, source_label, reviewed_at
        ) VALUES
        ('policy_housing_001', 'housing', 'Newlywed Rent Deposit Support', 'Seoul Housing Office', 'Seoul', 'Rent deposit interest support for newlywed households.', '2026-01-01 to 2026-12-31', 'Interest subsidy', 'APPROVED', true, 'https://example.go.kr/policies/housing-001', 'Official notice', '2026-08-01'),
        ('policy_housing_002', 'housing', 'Starter Home Lease Support', 'Gyeonggi Housing Bureau', 'Gyeonggi', 'Lease support for households preparing marriage.', '2026-02-01 to budget exhaustion', 'Lease support', 'APPROVED', true, 'https://example.go.kr/policies/housing-002', 'Official notice', '2026-08-01'),
        ('policy_housing_003', 'housing', 'Youth Couple Move-in Grant', 'Incheon City', 'Incheon', 'Move-in grant for young newlywed couples.', '2026-03-01 to 2026-11-30', 'Grant', 'APPROVED', true, 'https://example.go.kr/policies/housing-003', 'Official notice', '2026-08-01'),
        ('policy_loan_001', 'loan', 'Marriage Preparation Loan', 'Korea Housing Finance Agency', 'National', 'Low-interest preparation loan for engaged couples.', 'Rolling', 'Loan', 'APPROVED', true, 'https://example.go.kr/policies/loan-001', 'Official page', '2026-08-01'),
        ('policy_loan_002', 'loan', 'New Household Credit Support', 'Local Credit Foundation', 'National', 'Credit support for newly formed households.', 'Rolling', 'Loan guarantee', 'APPROVED', true, 'https://example.go.kr/policies/loan-002', 'Official page', '2026-08-01'),
        ('policy_cash_001', 'cash', 'Marriage Celebration Grant', 'Daejeon City', 'Daejeon', 'Local celebration grant for registered marriage.', '2026-01-15 to 2026-12-15', 'Cash grant', 'APPROVED', true, 'https://example.go.kr/policies/cash-001', 'Official notice', '2026-08-01'),
        ('policy_cash_002', 'cash', 'New Couple Settlement Allowance', 'Busan City', 'Busan', 'Settlement allowance for newlywed local residents.', '2026-04-01 to 2026-10-31', 'Allowance', 'APPROVED', true, 'https://example.go.kr/policies/cash-002', 'Official notice', '2026-08-01'),
        ('policy_childcare_001', 'childcare', 'Pregnancy Health Voucher', 'Ministry of Health', 'National', 'Health voucher for pregnancy preparation and early pregnancy.', 'Rolling', 'Voucher', 'APPROVED', true, 'https://example.go.kr/policies/childcare-001', 'Official page', '2026-08-01'),
        ('policy_childcare_002', 'childcare', 'Infant Care Starter Kit', 'Sejong City', 'Sejong', 'Starter kit for first infant care.', '2026-01-01 to 2026-12-31', 'Goods support', 'APPROVED', true, 'https://example.go.kr/policies/childcare-002', 'Official notice', '2026-08-01'),
        ('policy_education_001', 'education', 'Premarital Financial Counseling', 'Family Support Center', 'National', 'Counseling program for household budgeting.', 'Rolling', 'Counseling', 'APPROVED', true, 'https://example.go.kr/policies/education-001', 'Official page', '2026-08-01'),
        ('policy_education_002', 'education', 'Newlywed Housing Class', 'Housing Welfare Institute', 'National', 'Education program for housing contracts and public support.', 'Quarterly', 'Education', 'APPROVED', true, 'https://example.go.kr/policies/education-002', 'Official page', '2026-08-01'),
        ('policy_cash_003', 'cash', 'Small City Wedding Hall Discount', 'Small City Office', 'Jeonbuk', 'Public facility discount for wedding ceremonies.', '2026-05-01 to 2026-12-31', 'Discount', 'APPROVED', true, 'https://example.go.kr/policies/cash-003', 'Official notice', '2026-08-01'),
        ('policy_inactive_001', 'housing', 'Expired Housing Pilot', 'Pilot Agency', 'National', 'Expired pilot policy that must not be exposed.', '2025-01-01 to 2025-12-31', 'Pilot support', 'DRAFT', false, 'https://example.go.kr/policies/inactive-001', 'Archived notice', '2026-08-01')
        ON CONFLICT (id) DO UPDATE SET
            category_code = EXCLUDED.category_code,
            title = EXCLUDED.title,
            agency = EXCLUDED.agency,
            region = EXCLUDED.region,
            summary = EXCLUDED.summary,
            application_period = EXCLUDED.application_period,
            support_type = EXCLUDED.support_type,
            status = EXCLUDED.status,
            is_active = EXCLUDED.is_active,
            official_source_url = EXCLUDED.official_source_url,
            source_label = EXCLUDED.source_label,
            reviewed_at = EXCLUDED.reviewed_at;
        """
    )
    op.execute(
        """
        INSERT INTO question (id, policy_id, fact_key, prompt, answer_type, required, sort_order)
        SELECT 'q_' || id || '_region', id, 'region', 'Confirm your residential region.', 'single_select', true, 10
        FROM policy
        ON CONFLICT (id) DO UPDATE SET prompt = EXCLUDED.prompt, answer_type = EXCLUDED.answer_type;
        """
    )
    op.execute(
        """
        INSERT INTO policy_rule (id, policy_id, rule_type, fact_key, operator, value_text, required, evidence_text)
        SELECT 'rule_' || id || '_region', id, 'eligibility', 'region', 'in', region, true, 'Applicant region must match the policy region or national scope.'
        FROM policy
        ON CONFLICT (id) DO UPDATE SET value_text = EXCLUDED.value_text, evidence_text = EXCLUDED.evidence_text;
        """
    )
    op.execute(
        """
        INSERT INTO policy_document (id, policy_id, title, url, document_type, official_source, reviewed_at, collected_at, document_hash)
        SELECT 'doc_' || id, id, title || ' Source Document', official_source_url, 'official_notice', source_label, reviewed_at, '2026-08-05T00:00:00Z', 'sha256:' || id
        FROM policy
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            url = EXCLUDED.url,
            official_source = EXCLUDED.official_source,
            reviewed_at = EXCLUDED.reviewed_at,
            document_hash = EXCLUDED.document_hash;
        """
    )
    op.execute(
        """
        INSERT INTO policy_relation (id, source_policy_id, target_policy_id, relation_type) VALUES
        ('rel_housing_loan_001', 'policy_housing_001', 'policy_loan_001', 'related_support'),
        ('rel_cash_childcare_001', 'policy_cash_001', 'policy_childcare_001', 'life_event_next_step')
        ON CONFLICT (id) DO UPDATE SET relation_type = EXCLUDED.relation_type;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_policy_relation_target_policy_id", table_name="policy_relation")
    op.drop_index("ix_policy_relation_source_policy_id", table_name="policy_relation")
    op.drop_table("policy_relation")
    op.drop_index("ix_policy_document_policy_id", table_name="policy_document")
    op.drop_table("policy_document")
    op.drop_index("ix_policy_rule_policy_id", table_name="policy_rule")
    op.drop_table("policy_rule")
    op.drop_index("ix_question_policy_id", table_name="question")
    op.drop_table("question")
    op.drop_index("ix_policy_is_active", table_name="policy")
    op.drop_index("ix_policy_status", table_name="policy")
    op.drop_index("ix_policy_category_code", table_name="policy")
    op.drop_table("policy")
    op.drop_table("category")