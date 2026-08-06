from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog.models import ApprovalStatus, Policy, PolicyEvaluation, PolicyStatus
from app.modules.eligibility.rules import EvaluationState


async def list_active_policies_for_category(db: AsyncSession, category_code: str) -> list[Policy]:
    result = await db.execute(
        select(Policy)
        .options(selectinload(Policy.rules))
        .where(
            Policy.category_code == category_code,
            Policy.status == PolicyStatus.APPROVED,
            Policy.is_active.is_(True),
        )
        .order_by(Policy.title, Policy.id)
    )
    policies = list(result.scalars().all())
    evaluable: list[Policy] = []
    for policy in policies:
        approved_rules = [rule for rule in policy.rules if rule.approval_status == ApprovalStatus.APPROVED]
        if approved_rules:
            policy.rules = approved_rules
            evaluable.append(policy)
    return evaluable


async def get_active_policy_with_rules(db: AsyncSession, policy_id: str) -> Policy | None:
    result = await db.execute(
        select(Policy)
        .options(selectinload(Policy.rules))
        .where(
            Policy.id == policy_id,
            Policy.status == PolicyStatus.APPROVED,
            Policy.is_active.is_(True),
        )
    )
    policy = result.scalar_one_or_none()
    if policy is not None:
        approved_rules = [rule for rule in policy.rules if rule.approval_status == ApprovalStatus.APPROVED]
        if not approved_rules:
            return None
        policy.rules = approved_rules
    return policy


async def upsert_policy_evaluation(
    db: AsyncSession,
    *,
    session_id: int,
    policy_id: str,
    eligibility_status: str,
    evaluation_state: str,
    recommendation_score: int,
    evidence: dict[str, Any],
    fact_snapshot: dict[str, Any],
) -> PolicyEvaluation:
    statement = (
        insert(PolicyEvaluation)
        .values(
            session_id=session_id,
            policy_id=policy_id,
            eligibility_status=eligibility_status,
            evaluation_state=evaluation_state,
            recommendation_score=recommendation_score,
            evidence=evidence,
            fact_snapshot=fact_snapshot,
        )
        .on_conflict_do_update(
            constraint="uq_policy_evaluation_session_policy",
            set_={
                "eligibility_status": eligibility_status,
                "evaluation_state": evaluation_state,
                "recommendation_score": recommendation_score,
                "evidence": evidence,
                "fact_snapshot": fact_snapshot,
                "updated_at": func.now(),
            },
        )
        .returning(PolicyEvaluation)
    )
    result = await db.execute(statement)
    return result.scalar_one()


async def list_session_evaluations(db: AsyncSession, session_id: int) -> list[PolicyEvaluation]:
    result = await db.execute(
        select(PolicyEvaluation)
        .where(PolicyEvaluation.session_id == session_id)
        .order_by(PolicyEvaluation.recommendation_score.desc(), PolicyEvaluation.policy_id)
    )
    return list(result.scalars().all())


async def get_session_policy_evaluation(
    db: AsyncSession,
    session_id: int,
    policy_id: str,
) -> PolicyEvaluation | None:
    result = await db.execute(
        select(PolicyEvaluation).where(
            PolicyEvaluation.session_id == session_id,
            PolicyEvaluation.policy_id == policy_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_session_evaluations_for_category(db: AsyncSession, session_id: int, category_code: str) -> int:
    policy_ids = select(Policy.id).where(
        Policy.category_code == category_code,
        Policy.status == PolicyStatus.APPROVED,
        Policy.is_active.is_(True),
    )
    result = await db.execute(
        delete(PolicyEvaluation).where(
            PolicyEvaluation.session_id == session_id,
            PolicyEvaluation.policy_id.in_(policy_ids),
        )
    )
    return result.rowcount or 0


async def mark_session_evaluations_stale(db: AsyncSession, session_id: int) -> int:
    result = await db.execute(
        update(PolicyEvaluation)
        .where(
            PolicyEvaluation.session_id == session_id,
            PolicyEvaluation.evaluation_state == EvaluationState.ACTIVE,
        )
        .values(evaluation_state=EvaluationState.STALE)
    )
    return result.rowcount or 0
