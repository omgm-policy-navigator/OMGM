from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.catalog.models import Category, Policy, PolicyDocument, PolicyRelation, PolicyRule, PolicyStatus, Question
from app.core.config import AppConfig
from app.db.session import create_engine
from app.modules.policies import PolicySeedCatalog, load_policy_seed

REVIEWED_AT = date(2026, 8, 1)
COLLECTED_AT = datetime(2026, 8, 5, tzinfo=UTC)

SOURCE_CATEGORY_TO_DB_CATEGORY: dict[str, tuple[str, str, int, str]] = {
    "1": ("housing", "주거", 10, "임대주택, 보증금, 월세·주거비 지원"),
    "2": ("loan", "대출", 20, "전세·주택구입 정책대출 및 이자지원"),
    "3": ("cash", "웨딩", 30, "공공예식장, 결혼 준비·살림비 지원"),
    "4": ("education", "세제 혜택", 50, "혼인·자녀·주거 관련 세액공제와 비과세"),
    "5": ("childcare", "출산·육아", 40, "임신, 출산, 산후조리, 양육·돌봄 지원"),
}

POLICY_ID_PREFIX_BY_CATEGORY: dict[str, str] = {
    "housing": "policy_housing",
    "loan": "policy_loan",
    "cash": "policy_cash",
    "education": "policy_education",
    "childcare": "policy_childcare",
}

SUPPORT_TYPE_BY_CATEGORY: dict[str, str] = {
    "housing": "주거 지원",
    "loan": "정책대출",
    "cash": "결혼 지원",
    "education": "세제 혜택",
    "childcare": "출산·육아 지원",
}

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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.APPROVED,
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
        "status": PolicyStatus.DRAFT,
        "is_active": False,
        "official_source_url": "https://example.go.kr/policies/inactive-001",
        "source_label": "Archived notice",
        "reviewed_at": REVIEWED_AT,
    },
]


def question_rows(policies: list[dict[str, Any]] = POLICY_SEED_DATA) -> list[dict[str, Any]]:
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
        for policy in policies
    ]


def rule_rows(policies: list[dict[str, Any]] = POLICY_SEED_DATA) -> list[dict[str, Any]]:
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
        for policy in policies
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


def application_period(start: date | None, end: date | None) -> str:
    if start is not None and end is not None:
        return f"{start.isoformat()} to {end.isoformat()}"
    if start is not None:
        return f"{start.isoformat()}부터"
    if end is not None:
        return f"{end.isoformat()}까지"
    return "공식 공고 확인"


def reviewed_seed_payload(
    catalog: PolicySeedCatalog,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, str],
]:
    categories = [
        {"code": code, "name": name, "description": description, "sort_order": sort_order}
        for code, name, sort_order, description in SOURCE_CATEGORY_TO_DB_CATEGORY.values()
    ]
    counters = {code: 0 for code in POLICY_ID_PREFIX_BY_CATEGORY}
    policy_id_map: dict[str, str] = {}
    policies: list[dict[str, Any]] = []

    for source_policy in sorted(catalog.policies.values(), key=lambda item: int(item.id)):
        category_code, _name, _sort_order, _description = SOURCE_CATEGORY_TO_DB_CATEGORY[source_policy.category_id]
        counters[category_code] += 1
        policy_id = f"{POLICY_ID_PREFIX_BY_CATEGORY[category_code]}_{counters[category_code]:03d}"
        policy_id_map[source_policy.id] = policy_id
        policies.append(
            {
                "id": policy_id,
                "category_code": category_code,
                "title": source_policy.name,
                "agency": source_policy.managing_agency,
                "region": region_from_policy(source_policy.name, source_policy.summary),
                "summary": source_policy.summary,
                "application_period": application_period(
                    source_policy.application_start_date,
                    source_policy.application_end_date,
                ),
                "support_type": SUPPORT_TYPE_BY_CATEGORY[category_code],
                "status": PolicyStatus.APPROVED,
                "is_active": True,
                "official_source_url": source_policy.application_url,
                "source_label": "공식 신청/안내 페이지",
                "reviewed_at": source_policy.verified_at,
            }
        )

    documents = [
        {
            "id": f"doc_{policy_id_map[document.policy_id]}",
            "policy_id": policy_id_map[document.policy_id],
            "title": document.title,
            "url": document.source_url,
            "document_type": str(document.document_type),
            "official_source": "공식 출처",
            "reviewed_at": catalog.policies[document.policy_id].verified_at,
            "collected_at": COLLECTED_AT,
            "document_hash": f"sha256:{policy_id_map[document.policy_id]}",
        }
        for document in catalog.documents
        if document.policy_id in policy_id_map
    ]
    relations = [
        {
            "id": f"rel_{relation.id}",
            "source_policy_id": policy_id_map[relation.from_policy_id],
            "target_policy_id": policy_id_map[relation.to_policy_id],
            "relation_type": str(relation.relation_type).lower(),
        }
        for relation in catalog.relations
        if relation.from_policy_id in policy_id_map and relation.to_policy_id in policy_id_map
    ]
    return categories, policies, documents, relations, policy_id_map


def region_from_policy(name: str, summary: str) -> str:
    text = f"{name} {summary}"
    if "서울" in text:
        return "Seoul"
    if "경기" in text:
        return "Gyeonggi"
    if "인천" in text:
        return "Incheon"
    if "부산" in text:
        return "Busan"
    if "대전" in text:
        return "Daejeon"
    if "전북" in text:
        return "Jeonbuk"
    if "세종" in text:
        return "Sejong"
    return "National"


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
    catalog = load_policy_seed(AppConfig.from_env().policy_seed_dir)
    categories, policies, documents, relations, _policy_id_map = reviewed_seed_payload(catalog)
    await upsert_rows(session, Category, categories, ["code"])
    await upsert_rows(session, Policy, policies, ["id"])
    await upsert_rows(session, Question, question_rows(policies), ["id"])
    await upsert_rows(session, PolicyRule, rule_rows(policies), ["id"])
    await upsert_rows(session, PolicyDocument, documents, ["id"])
    await upsert_rows(session, PolicyRelation, relations, ["id"])
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
