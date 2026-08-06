from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import Category, Policy, PolicyEvaluation, PolicyRelation, PolicyStatus
from app.modules.graph.projection import GraphCategory, GraphEvaluation, GraphPolicy, GraphRelation


async def list_graph_categories(db: AsyncSession, category_code: str | None = None) -> list[GraphCategory]:
    statement = select(Category).order_by(Category.sort_order, Category.code)
    if category_code is not None:
        statement = statement.where(Category.code == category_code)
    result = await db.execute(statement)
    return [GraphCategory(code=category.code, name=category.name) for category in result.scalars().all()]


async def list_graph_policies(db: AsyncSession, category_code: str | None = None) -> list[GraphPolicy]:
    statement = (
        select(Policy)
        .where(Policy.status == PolicyStatus.APPROVED, Policy.is_active.is_(True))
        .order_by(Policy.title, Policy.id)
    )
    if category_code is not None:
        statement = statement.where(Policy.category_code == category_code)
    result = await db.execute(statement)
    return [
        GraphPolicy(
            id=policy.id,
            category_code=policy.category_code,
            title=policy.title,
            region=policy.region,
            support_type=policy.support_type,
        )
        for policy in result.scalars().all()
    ]


async def list_graph_evaluations(db: AsyncSession, session_id: int) -> list[GraphEvaluation]:
    result = await db.execute(
        select(PolicyEvaluation)
        .where(PolicyEvaluation.session_id == session_id)
        .order_by(PolicyEvaluation.recommendation_score.desc(), PolicyEvaluation.policy_id)
    )
    return [
        GraphEvaluation(
            policy_id=evaluation.policy_id,
            eligibility_status=evaluation.eligibility_status,
            evaluation_state=evaluation.evaluation_state,
            recommendation_score=evaluation.recommendation_score,
            evidence=evaluation.evidence,
        )
        for evaluation in result.scalars().all()
    ]


async def list_graph_relations(db: AsyncSession, policy_ids: set[str]) -> list[GraphRelation]:
    if not policy_ids:
        return []
    result = await db.execute(
        select(PolicyRelation)
        .where(
            PolicyRelation.source_policy_id.in_(policy_ids),
            PolicyRelation.target_policy_id.in_(policy_ids),
        )
        .order_by(PolicyRelation.id)
    )
    return [
        GraphRelation(
            id=relation.id,
            source_policy_id=relation.source_policy_id,
            target_policy_id=relation.target_policy_id,
            relation_type=relation.relation_type,
        )
        for relation in result.scalars().all()
    ]