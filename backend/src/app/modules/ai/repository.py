from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog.models import ApprovalStatus, Policy, PolicyDocument, PolicyEvaluation, PolicyStatus


@dataclass(frozen=True)
class PolicyEvidenceBundle:
    policy: Policy
    evaluation: PolicyEvaluation | None
    documents: tuple[PolicyDocument, ...]


async def get_policy_evidence_bundle(
    db: AsyncSession,
    *,
    session_id: int,
    policy_id: str,
) -> PolicyEvidenceBundle | None:
    result = await db.execute(
        select(Policy)
        .options(selectinload(Policy.documents), selectinload(Policy.rules))
        .where(
            Policy.id == policy_id,
            Policy.status == PolicyStatus.APPROVED,
            Policy.is_active.is_(True),
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        return None

    evaluation_result = await db.execute(
        select(PolicyEvaluation).where(
            PolicyEvaluation.session_id == session_id,
            PolicyEvaluation.policy_id == policy_id,
        )
    )
    evaluation = evaluation_result.scalar_one_or_none()
    policy.rules = [rule for rule in policy.rules if rule.approval_status == ApprovalStatus.APPROVED]
    documents = tuple(
        document for document in policy.documents if document.approval_status == ApprovalStatus.APPROVED
    )
    return PolicyEvidenceBundle(policy=policy, evaluation=evaluation, documents=documents)


async def get_top_session_policy_evidence_bundle(
    db: AsyncSession,
    *,
    session_id: int,
    category_code: str | None = None,
) -> PolicyEvidenceBundle | None:
    return await get_ranked_session_policy_evidence_bundle(
        db,
        session_id=session_id,
        category_code=category_code,
        rank=1,
    )


async def get_ranked_session_policy_evidence_bundle(
    db: AsyncSession,
    *,
    session_id: int,
    category_code: str | None = None,
    rank: int = 1,
) -> PolicyEvidenceBundle | None:
    if rank < 1:
        return None

    statement = (
        select(PolicyEvaluation)
        .join(Policy, Policy.id == PolicyEvaluation.policy_id)
        .where(
            PolicyEvaluation.session_id == session_id,
            Policy.status == PolicyStatus.APPROVED,
            Policy.is_active.is_(True),
        )
        .order_by(PolicyEvaluation.recommendation_score.desc(), PolicyEvaluation.policy_id)
        .offset(rank - 1)
        .limit(1)
    )
    if category_code is not None:
        statement = statement.where(Policy.category_code == category_code)

    result = await db.execute(statement)
    evaluation = result.scalar_one_or_none()
    if evaluation is None:
        return None
    return await get_policy_evidence_bundle(db, session_id=session_id, policy_id=evaluation.policy_id)


def _normalize_search_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _policy_match_score(policy: Policy, message: str) -> int:
    normalized_message = _normalize_search_text(message)
    if not normalized_message:
        return 0

    score = 0
    fields = (policy.title, policy.summary, policy.agency, policy.region, policy.support_type)
    for field in fields:
        normalized_field = _normalize_search_text(str(field))
        if not normalized_field:
            continue
        if normalized_field in normalized_message:
            score += 100
        if normalized_message in normalized_field:
            score += 70

    title_text = policy.title.replace("·", " ").replace("(", " ").replace(")", " ")
    title_tokens = [token for token in title_text.split() if token]
    summary_tokens = [token for token in policy.summary.replace("·", " ").split() if token]
    for token in (*title_tokens, *summary_tokens[:8]):
        normalized_token = _normalize_search_text(token)
        if len(normalized_token) >= 2 and normalized_token in normalized_message:
            score += 10

    return score


async def find_policy_evidence_bundle_for_message(
    db: AsyncSession,
    *,
    session_id: int,
    category_code: str | None,
    message: str,
) -> PolicyEvidenceBundle | None:
    statement = (
        select(Policy)
        .options(selectinload(Policy.documents), selectinload(Policy.rules))
        .where(
            Policy.status == PolicyStatus.APPROVED,
            Policy.is_active.is_(True),
        )
        .order_by(Policy.title, Policy.id)
    )
    if category_code is not None:
        statement = statement.where(Policy.category_code == category_code)

    result = await db.execute(statement)
    candidates = list(result.scalars().all())
    scored = sorted(
        ((_policy_match_score(policy, message), policy) for policy in candidates),
        key=lambda item: (-item[0], item[1].title, item[1].id),
    )
    if not scored or scored[0][0] < 70:
        return None

    policy = scored[0][1]
    policy.rules = [rule for rule in policy.rules if rule.approval_status == ApprovalStatus.APPROVED]
    evaluation_result = await db.execute(
        select(PolicyEvaluation).where(
            PolicyEvaluation.session_id == session_id,
            PolicyEvaluation.policy_id == policy.id,
        )
    )
    return PolicyEvidenceBundle(
        policy=policy,
        evaluation=evaluation_result.scalar_one_or_none(),
        documents=tuple(
            document for document in policy.documents if document.approval_status == ApprovalStatus.APPROVED
        ),
    )
