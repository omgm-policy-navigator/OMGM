from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import Category, Policy, PolicyEvaluation, PolicyRelation, PolicyStatus
from app.modules.graph.projection import GraphCategory, GraphEvaluation, GraphPolicy, GraphRelation


async def list_graph_categories(db: AsyncSession, category_code: str | None = None) -> list[GraphCategory]:
    statement = select(Category).order_by(Category.sort_order, Category.code)
    if category_code is not None:
        statement = statement.where(Category.code == category_code)
    result = await db.execute(statement)
    return [GraphCategory(code=category.code, name=category.name) for category in result.scalars().all()]


async def list_graph_policies(
    db: AsyncSession,
    category_code: str | None = None,
    policy_ids: set[str] | None = None,
) -> list[GraphPolicy]:
    if policy_ids is not None and not policy_ids:
        return []
    statement = (
        select(Policy)
        .where(Policy.status == PolicyStatus.APPROVED, Policy.is_active.is_(True))
        .order_by(Policy.title, Policy.id)
    )
    if category_code is not None:
        statement = statement.where(Policy.category_code == category_code)
    if policy_ids is not None:
        statement = statement.where(Policy.id.in_(policy_ids))
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


async def list_graph_evaluations(
    db: AsyncSession,
    session_id: int,
    policy_ids: set[str] | None = None,
) -> list[GraphEvaluation]:
    if policy_ids is not None and not policy_ids:
        return []
    statement = (
        select(PolicyEvaluation)
        .where(PolicyEvaluation.session_id == session_id)
        .order_by(PolicyEvaluation.recommendation_score.desc(), PolicyEvaluation.policy_id)
    )
    if policy_ids is not None:
        statement = statement.where(PolicyEvaluation.policy_id.in_(policy_ids))
    result = await db.execute(statement)
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
    return [_relation_to_graph(relation) for relation in result.scalars().all()]


async def list_centered_graph_policy_ids(
    db: AsyncSession,
    policy_id: str,
    *,
    max_depth: int,
    category_code: str | None = None,
) -> set[str]:
    visited = {policy_id}
    frontier = {policy_id}
    for _depth in range(max_depth):
        result = await db.execute(
            select(PolicyRelation).where(
                or_(
                    PolicyRelation.source_policy_id.in_(frontier),
                    PolicyRelation.target_policy_id.in_(frontier),
                )
            )
        )
        next_frontier: set[str] = set()
        for relation in result.scalars().all():
            if relation.source_policy_id in frontier and relation.target_policy_id not in visited:
                next_frontier.add(relation.target_policy_id)
            if relation.target_policy_id in frontier and relation.source_policy_id not in visited:
                next_frontier.add(relation.source_policy_id)
        frontier = next_frontier - visited
        visited.update(next_frontier)
        if not frontier:
            break
    if category_code is None:
        return visited
    filtered = await list_graph_policies(db, category_code=category_code, policy_ids=visited)
    return {policy.id for policy in filtered}


def _relation_to_graph(relation: PolicyRelation) -> GraphRelation:
    return GraphRelation(
        id=relation.id,
        source_policy_id=relation.source_policy_id,
        target_policy_id=relation.target_policy_id,
        relation_type=relation.relation_type,
    )