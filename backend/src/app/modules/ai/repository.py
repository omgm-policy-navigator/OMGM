from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog.models import Policy, PolicyDocument, PolicyEvaluation, PolicyStatus


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
        .options(selectinload(Policy.documents))
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
    return PolicyEvidenceBundle(policy=policy, evaluation=evaluation, documents=tuple(policy.documents))


async def get_top_session_policy_evidence_bundle(
    db: AsyncSession,
    *,
    session_id: int,
) -> PolicyEvidenceBundle | None:
    result = await db.execute(
        select(PolicyEvaluation)
        .where(PolicyEvaluation.session_id == session_id)
        .order_by(PolicyEvaluation.recommendation_score.desc(), PolicyEvaluation.policy_id)
        .limit(1)
    )
    evaluation = result.scalar_one_or_none()
    if evaluation is None:
        return None
    return await get_policy_evidence_bundle(db, session_id=session_id, policy_id=evaluation.policy_id)
