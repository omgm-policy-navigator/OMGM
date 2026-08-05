from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog.models import Category, Policy, PolicyDocument
from app.catalog.schemas import (
    CategoryResponse,
    PolicyDetailResponse,
    PolicyDocumentResponse,
    PolicySourceResponse,
    PolicySummaryResponse,
)

APPROVED_POLICY_STATUS = "APPROVED"


def category_to_response(category: Category) -> CategoryResponse:
    return CategoryResponse.model_validate(category)


def policy_to_summary(policy: Policy) -> PolicySummaryResponse:
    return PolicySummaryResponse(
        policyId=policy.id,
        categoryCode=policy.category_code,
        title=policy.title,
        agency=policy.agency,
        region=policy.region,
        applicationPeriod=policy.application_period,
        status=policy.status,
        officialSourceUrl=policy.official_source_url,
        reviewedAt=policy.reviewed_at,
    )


def policy_to_detail(policy: Policy) -> PolicyDetailResponse:
    return PolicyDetailResponse(
        policyId=policy.id,
        categoryCode=policy.category_code,
        title=policy.title,
        agency=policy.agency,
        region=policy.region,
        summary=policy.summary,
        applicationPeriod=policy.application_period,
        supportType=policy.support_type,
        status=policy.status,
        source=PolicySourceResponse(
            label=policy.source_label,
            url=policy.official_source_url,
            reviewedAt=policy.reviewed_at,
        ),
    )


def document_to_response(document: PolicyDocument) -> PolicyDocumentResponse:
    return PolicyDocumentResponse(
        documentId=document.id,
        policyId=document.policy_id,
        title=document.title,
        url=document.url,
        documentType=document.document_type,
        officialSource=document.official_source,
        reviewedAt=document.reviewed_at,
        collectedAt=document.collected_at,
        documentHash=document.document_hash,
    )


def approved_policy_filters(policy_id: str):
    return (
        Policy.id == policy_id,
        Policy.status == APPROVED_POLICY_STATUS,
        Policy.is_active.is_(True),
    )


async def list_categories(session: AsyncSession) -> list[CategoryResponse]:
    result = await session.execute(select(Category).order_by(Category.sort_order, Category.code))
    return [category_to_response(category) for category in result.scalars().all()]


async def list_policies_by_category(session: AsyncSession, category_code: str) -> list[PolicySummaryResponse]:
    result = await session.execute(
        select(Policy)
        .where(
            Policy.category_code == category_code,
            Policy.status == APPROVED_POLICY_STATUS,
            Policy.is_active.is_(True),
        )
        .order_by(Policy.title, Policy.id)
    )
    return [policy_to_summary(policy) for policy in result.scalars().all()]


async def get_approved_policy(session: AsyncSession, policy_id: str) -> PolicyDetailResponse | None:
    result = await session.execute(
        select(Policy)
        .options(selectinload(Policy.documents), selectinload(Policy.rules))
        .where(*approved_policy_filters(policy_id))
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        return None
    return policy_to_detail(policy)


async def list_policy_documents(session: AsyncSession, policy_id: str) -> list[PolicyDocumentResponse] | None:
    result = await session.execute(
        select(Policy).options(selectinload(Policy.documents)).where(*approved_policy_filters(policy_id))
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        return None

    documents = sorted(policy.documents, key=lambda document: document.title)
    return [document_to_response(document) for document in documents]