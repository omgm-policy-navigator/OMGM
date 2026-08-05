from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.catalog.models import Category, Policy, PolicyDocument, PolicyRelation, PolicyRule, Question
from app.core.config import AppConfig
from app.db.session import create_engine

REVIEWED_AT = date(2026, 8, 1)
COLLECTED_AT = datetime(2026, 8, 5, tzinfo=UTC)

CATEGORY_SEED_DATA: list[dict[str, Any]] = [
    {"code": "housing", "name": "Housing", "description": "Housing and rent support", "sort_order": 10},
    {"code": "loan", "name": "Loan", "description": "Marriage and household loan support", "sort_order": 20},
    {"code": "cash", "name": "Cash Benefit", "description": "Direct allowance and grant support", "sort_order": 30},
    {"code": "childcare", "name": "Childcare", "description": "Pregnancy and childcare support", "sort_order": 40},
    {"code": "education", "name": "Education", "description": "Counseling and education programs", "sort_order": 50},
]

POLICY_SEED_DATA: list[dict[str, Any]] = [
    {
        "id": "policy_housing_001",
        "category_code": "housing",
        "title": "Newlywed Rent Deposit Support",
        "agency": "Seoul Housing Office",
        "region": "Seoul",
        "summary": "Rent deposit interest support for newlywed households.",
        "application_period": "2026-01-01 to 2026-12-31",
        "support_type": "Interest subsidy",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/housing-001",
        "source_label": "Official notice",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_housing_002",
        "category_code": "housing",
        "title": "Starter Home Lease Support",
        "agency": "Gyeonggi Housing Bureau",
        "region": "Gyeonggi",
        "summary": "Lease support for households preparing marriage.",
        "application_period": "2026-02-01 to budget exhaustion",
        "support_type": "Lease support",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/housing-002",
        "source_label": "Official notice",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_housing_003",
        "category_code": "housing",
        "title": "Youth Couple Move-in Grant",
        "agency": "Incheon City",
        "region": "Incheon",
        "summary": "Move-in grant for young newlywed couples.",
        "application_period": "2026-03-01 to 2026-11-30",
        "support_type": "Grant",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/housing-003",
        "source_label": "Official notice",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_loan_001",
        "category_code": "loan",
        "title": "Marriage Preparation Loan",
        "agency": "Korea Housing Finance Agency",
        "region": "National",
        "summary": "Low-interest preparation loan for engaged couples.",
        "application_period": "Rolling",
        "support_type": "Loan",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/loan-001",
        "source_label": "Official page",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_loan_002",
        "category_code": "loan",
        "title": "New Household Credit Support",
        "agency": "Local Credit Foundation",
        "region": "National",
        "summary": "Credit support for newly formed households.",
        "application_period": "Rolling",
        "support_type": "Loan guarantee",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/loan-002",
        "source_label": "Official page",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_cash_001",
        "category_code": "cash",
        "title": "Marriage Celebration Grant",
        "agency": "Daejeon City",
        "region": "Daejeon",
        "summary": "Local celebration grant for registered marriage.",
        "application_period": "2026-01-15 to 2026-12-15",
        "support_type": "Cash grant",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/cash-001",
        "source_label": "Official notice",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_cash_002",
        "category_code": "cash",
        "title": "New Couple Settlement Allowance",
        "agency": "Busan City",
        "region": "Busan",
        "summary": "Settlement allowance for newlywed local residents.",
        "application_period": "2026-04-01 to 2026-10-31",
        "support_type": "Allowance",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/cash-002",
        "source_label": "Official notice",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_childcare_001",
        "category_code": "childcare",
        "title": "Pregnancy Health Voucher",
        "agency": "Ministry of Health",
        "region": "National",
        "summary": "Health voucher for pregnancy preparation and early pregnancy.",
        "application_period": "Rolling",
        "support_type": "Voucher",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/childcare-001",
        "source_label": "Official page",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_childcare_002",
        "category_code": "childcare",
        "title": "Infant Care Starter Kit",
        "agency": "Sejong City",
        "region": "Sejong",
        "summary": "Starter kit for first infant care.",
        "application_period": "2026-01-01 to 2026-12-31",
        "support_type": "Goods support",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/childcare-002",
        "source_label": "Official notice",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_education_001",
        "category_code": "education",
        "title": "Premarital Financial Counseling",
        "agency": "Family Support Center",
        "region": "National",
        "summary": "Counseling program for household budgeting.",
        "application_period": "Rolling",
        "support_type": "Counseling",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/education-001",
        "source_label": "Official page",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_education_002",
        "category_code": "education",
        "title": "Newlywed Housing Class",
        "agency": "Housing Welfare Institute",
        "region": "National",
        "summary": "Education program for housing contracts and public support.",
        "application_period": "Quarterly",
        "support_type": "Education",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/education-002",
        "source_label": "Official page",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_cash_003",
        "category_code": "cash",
        "title": "Small City Wedding Hall Discount",
        "agency": "Small City Office",
        "region": "Jeonbuk",
        "summary": "Public facility discount for wedding ceremonies.",
        "application_period": "2026-05-01 to 2026-12-31",
        "support_type": "Discount",
        "status": "APPROVED",
        "is_active": True,
        "official_source_url": "https://example.go.kr/policies/cash-003",
        "source_label": "Official notice",
        "reviewed_at": REVIEWED_AT,
    },
    {
        "id": "policy_inactive_001",
        "category_code": "housing",
        "title": "Expired Housing Pilot",
        "agency": "Pilot Agency",
        "region": "National",
        "summary": "Expired pilot policy that must not be exposed.",
        "application_period": "2025-01-01 to 2025-12-31",
        "support_type": "Pilot support",
        "status": "DRAFT",
        "is_active": False,
        "official_source_url": "https://example.go.kr/policies/inactive-001",
        "source_label": "Archived notice",
        "reviewed_at": REVIEWED_AT,
    },
]


def question_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": f"q_{policy['id']}_region",
            "policy_id": policy["id"],
            "fact_key": "region",
            "prompt": "Confirm your residential region.",
            "answer_type": "single_select",
            "required": True,
            "sort_order": 10,
        }
        for policy in POLICY_SEED_DATA
    ]


def rule_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": f"rule_{policy['id']}_region",
            "policy_id": policy["id"],
            "rule_type": "eligibility",
            "fact_key": "region",
            "operator": "in",
            "value_text": policy["region"],
            "required": True,
            "evidence_text": "Applicant region must match the policy region or national scope.",
        }
        for policy in POLICY_SEED_DATA
    ]


def document_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": f"doc_{policy['id']}",
            "policy_id": policy["id"],
            "title": f"{policy['title']} Source Document",
            "url": policy["official_source_url"],
            "document_type": "official_notice",
            "official_source": policy["source_label"],
            "reviewed_at": policy["reviewed_at"],
            "collected_at": COLLECTED_AT,
            "document_hash": f"sha256:{policy['id']}",
        }
        for policy in POLICY_SEED_DATA
    ]


POLICY_RELATION_SEED_DATA: list[dict[str, Any]] = [
    {
        "id": "rel_housing_loan_001",
        "source_policy_id": "policy_housing_001",
        "target_policy_id": "policy_loan_001",
        "relation_type": "related_support",
    },
    {
        "id": "rel_cash_childcare_001",
        "source_policy_id": "policy_cash_001",
        "target_policy_id": "policy_childcare_001",
        "relation_type": "life_event_next_step",
    },
]


async def upsert_rows(
    session: AsyncSession,
    model: type[Any],
    rows: list[dict[str, Any]],
    conflict_keys: list[str],
) -> None:
    for row in rows:
        statement = insert(model).values(**row)
        update_values = {key: statement.excluded[key] for key in row if key not in conflict_keys}
        statement = statement.on_conflict_do_update(index_elements=conflict_keys, set_=update_values)
        await session.execute(statement)


async def seed_database(session: AsyncSession) -> None:
    await upsert_rows(session, Category, CATEGORY_SEED_DATA, ["code"])
    await upsert_rows(session, Policy, POLICY_SEED_DATA, ["id"])
    await upsert_rows(session, Question, question_rows(), ["id"])
    await upsert_rows(session, PolicyRule, rule_rows(), ["id"])
    await upsert_rows(session, PolicyDocument, document_rows(), ["id"])
    await upsert_rows(session, PolicyRelation, POLICY_RELATION_SEED_DATA, ["id"])
    await session.commit()


async def run() -> None:
    config = AppConfig.from_env()
    engine = create_engine(config.database_url, config.database_pool_size, config.database_max_overflow)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_database(session)
    await engine.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()