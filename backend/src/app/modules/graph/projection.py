from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.graph.schemas import GraphEdgeResponse, GraphNodeResponse, SessionGraphResponse

DEFAULT_MAX_GRAPH_NODES = 80
MAX_GRAPH_NODES = 120
CENTERED_GRAPH_MAX_DEPTH = 2
USER_NODE_ID = "USER:anonymous"


@dataclass(frozen=True)
class GraphPolicy:
    id: str
    category_code: str
    title: str
    region: str
    support_type: str


@dataclass(frozen=True)
class GraphCategory:
    code: str
    name: str


@dataclass(frozen=True)
class GraphEvaluation:
    policy_id: str
    eligibility_status: str
    evaluation_state: str
    recommendation_score: int
    evidence: dict[str, Any]


@dataclass(frozen=True)
class GraphRelation:
    id: str
    source_policy_id: str
    target_policy_id: str
    relation_type: str


@dataclass(frozen=True)
class CandidateNode:
    node: GraphNodeResponse
    priority: tuple[int, int, str]


@dataclass
class GraphBuilder:
    max_nodes: int
    node_candidates: dict[str, CandidateNode] = field(default_factory=dict)
    edges: dict[str, GraphEdgeResponse] = field(default_factory=dict)

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        data: dict[str, Any] | None = None,
        priority: tuple[int, int, str] = (900, 0, ""),
    ) -> None:
        current = self.node_candidates.get(node_id)
        if current is not None and current.priority <= priority:
            return
        self.node_candidates[node_id] = CandidateNode(
            GraphNodeResponse(id=node_id, type=node_type, label=label, data=data or {}),
            priority,
        )

    def add_edge(
        self,
        edge_id: str,
        edge_type: str,
        source: str,
        target: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        if edge_id in self.edges:
            return
        self.edges[edge_id] = GraphEdgeResponse(
            id=edge_id,
            type=edge_type,
            source=source,
            target=target,
            data=data or {},
        )

    def response(self) -> SessionGraphResponse:
        ordered_candidates = sorted(self.node_candidates.values(), key=lambda candidate: candidate.priority)
        selected_nodes = [candidate.node for candidate in ordered_candidates[: self.max_nodes]]
        node_ids = {node.id for node in selected_nodes}
        valid_edges = [edge for edge in self.edges.values() if edge.source in node_ids and edge.target in node_ids]
        return SessionGraphResponse(
            nodes=selected_nodes,
            edges=valid_edges,
            nodeCount=len(selected_nodes),
            edgeCount=len(valid_edges),
            truncated=len(ordered_candidates) > len(selected_nodes),
        )


def normalize_max_nodes(value: int | None) -> int:
    if value is None:
        return DEFAULT_MAX_GRAPH_NODES
    return max(1, min(value, MAX_GRAPH_NODES))


def build_session_graph(
    *,
    facts: dict[str, Any],
    categories: list[GraphCategory],
    policies: list[GraphPolicy],
    evaluations: list[GraphEvaluation],
    relations: list[GraphRelation],
    selected_category_code: str | None,
    selected_policy_id: str | None,
    max_nodes: int | None = None,
) -> SessionGraphResponse:
    builder = GraphBuilder(max_nodes=normalize_max_nodes(max_nodes))
    builder.add_node(USER_NODE_ID, "USER", "Anonymous user", {"factCount": len(facts)}, _node_priority("USER"))

    category_by_code = {category.code: category for category in categories}
    policy_by_id = {policy.id: policy for policy in policies}
    evaluation_by_policy = {evaluation.policy_id: evaluation for evaluation in evaluations}
    visible_policy_ids = _visible_policy_ids(policies, relations, selected_category_code, selected_policy_id)

    for policy_id in visible_policy_ids:
        policy = policy_by_id.get(policy_id)
        if policy is None:
            continue
        category = category_by_code.get(policy.category_code)
        if category is not None:
            _add_category(builder, category, selected_category_code)
        _add_policy(builder, policy, evaluation_by_policy.get(policy.id), selected_policy_id)

    for fact_key, value in sorted(facts.items()):
        _add_condition(builder, fact_key, {"factKey": fact_key, "value": value}, direct=True)
        builder.add_edge(f"has_fact:{fact_key}", "HAS_FACT", USER_NODE_ID, _condition_node_id(fact_key))

    for policy_id in sorted(visible_policy_ids):
        policy = policy_by_id.get(policy_id)
        if policy is None:
            continue
        category = category_by_code.get(policy.category_code)
        policy_node_id = _policy_node_id(policy.id)
        if category is not None:
            builder.add_edge(
                f"category_policy:{category.code}:{policy.id}",
                "RECOMMENDS",
                _category_node_id(category.code),
                policy_node_id,
            )
        evaluation = evaluation_by_policy.get(policy.id)
        if evaluation is not None:
            _add_evaluation_edges(builder, evaluation, policy_node_id)
            action_node_id = _action_node_id(policy.id)
            builder.add_node(
                action_node_id,
                "ACTION",
                "Review application steps",
                {"policyId": policy.id},
                _node_priority("ACTION", policy_id=policy.id, selected_policy_id=selected_policy_id),
            )
            builder.add_edge(f"next_action:{policy.id}", "NEXT_ACTION", policy_node_id, action_node_id)

    for relation in relations:
        if relation.source_policy_id not in visible_policy_ids or relation.target_policy_id not in visible_policy_ids:
            continue
        edge_type = _relation_edge_type(relation.relation_type)
        builder.add_edge(
            f"relation:{relation.id}",
            edge_type,
            _policy_node_id(relation.source_policy_id),
            _policy_node_id(relation.target_policy_id),
            {"relationType": relation.relation_type},
        )

    return builder.response()


def _add_category(builder: GraphBuilder, category: GraphCategory, selected_category_code: str | None) -> None:
    builder.add_node(
        _category_node_id(category.code),
        "CATEGORY",
        category.name,
        {"categoryCode": category.code},
        _node_priority("CATEGORY", is_selected=category.code == selected_category_code),
    )
    builder.add_edge(f"selected:{category.code}", "SELECTED", USER_NODE_ID, _category_node_id(category.code))


def _add_policy(
    builder: GraphBuilder,
    policy: GraphPolicy,
    evaluation: GraphEvaluation | None,
    selected_policy_id: str | None,
) -> None:
    builder.add_node(
        _policy_node_id(policy.id),
        "POLICY",
        policy.title,
        {
            "policyId": policy.id,
            "categoryCode": policy.category_code,
            "region": policy.region,
            "supportType": policy.support_type,
            "eligibilityStatus": evaluation.eligibility_status if evaluation else None,
            "evaluationState": evaluation.evaluation_state if evaluation else None,
            "recommendationScore": evaluation.recommendation_score if evaluation else None,
        },
        _node_priority(
            "POLICY",
            policy_id=policy.id,
            selected_policy_id=selected_policy_id,
            eligibility_status=evaluation.eligibility_status if evaluation else None,
            recommendation_score=evaluation.recommendation_score if evaluation else 0,
        ),
    )


def _add_condition(
    builder: GraphBuilder,
    fact_key: str,
    data: dict[str, Any],
    *,
    direct: bool,
    selected_policy_id: str | None = None,
) -> None:
    builder.add_node(
        _condition_node_id(fact_key),
        "CONDITION",
        fact_key,
        data,
        _node_priority("CONDITION", is_direct=direct, selected_policy_id=selected_policy_id),
    )


def _visible_policy_ids(
    policies: list[GraphPolicy],
    relations: list[GraphRelation],
    selected_category_code: str | None,
    selected_policy_id: str | None,
) -> set[str]:
    policy_ids = {
        policy.id
        for policy in policies
        if selected_category_code is None or policy.category_code == selected_category_code
    }
    if selected_policy_id is None:
        return policy_ids
    return _bfs_policy_ids(policy_ids, relations, selected_policy_id, CENTERED_GRAPH_MAX_DEPTH)


def _bfs_policy_ids(
    policy_ids: set[str],
    relations: list[GraphRelation],
    selected_policy_id: str,
    max_depth: int,
) -> set[str]:
    if selected_policy_id not in policy_ids:
        return set()
    adjacency: dict[str, set[str]] = {policy_id: set() for policy_id in policy_ids}
    for relation in relations:
        if relation.source_policy_id in policy_ids and relation.target_policy_id in policy_ids:
            adjacency.setdefault(relation.source_policy_id, set()).add(relation.target_policy_id)
            adjacency.setdefault(relation.target_policy_id, set()).add(relation.source_policy_id)
    visited = {selected_policy_id}
    frontier = {selected_policy_id}
    for _depth in range(max_depth):
        next_frontier: set[str] = set()
        for policy_id in frontier:
            next_frontier.update(adjacency.get(policy_id, set()) - visited)
        frontier = next_frontier
        visited.update(next_frontier)
        if not frontier:
            break
    return visited


def _add_evaluation_edges(builder: GraphBuilder, evaluation: GraphEvaluation, policy_node_id: str) -> None:
    for bucket, edge_type in (
        ("satisfied", "MATCHES"),
        ("needsConfirmation", "MISSING_CONDITION"),
        ("unsatisfied", "FAILED_CONDITION"),
    ):
        for item in evaluation.evidence.get(bucket, []):
            fact_key = item.get("factKey")
            if not fact_key:
                continue
            normalized_fact_key = str(fact_key)
            _add_condition(
                builder,
                normalized_fact_key,
                {"factKey": normalized_fact_key},
                direct=True,
                selected_policy_id=evaluation.policy_id,
            )
            builder.add_edge(
                f"{edge_type.lower()}:{normalized_fact_key}:{evaluation.policy_id}",
                edge_type,
                _condition_node_id(normalized_fact_key),
                policy_node_id,
                {"ruleId": item.get("ruleId"), "required": item.get("required")},
            )


def _node_priority(
    node_type: str,
    *,
    policy_id: str | None = None,
    selected_policy_id: str | None = None,
    eligibility_status: str | None = None,
    recommendation_score: int = 0,
    is_direct: bool = False,
    is_selected: bool = False,
) -> tuple[int, int, str]:
    if node_type == "USER":
        return (0, 0, USER_NODE_ID)
    if node_type == "POLICY" and policy_id == selected_policy_id:
        return (10, -recommendation_score, policy_id or "")
    if node_type == "POLICY" and eligibility_status == "LIKELY_ELIGIBLE":
        return (20, -recommendation_score, policy_id or "")
    if node_type in {"ACTION", "CONDITION"} and (is_direct or policy_id == selected_policy_id):
        return (30, -recommendation_score, policy_id or "")
    if node_type == "CATEGORY" and is_selected:
        return (40, 0, "")
    if node_type == "POLICY":
        return (50, -recommendation_score, policy_id or "")
    if node_type == "CATEGORY":
        return (60, 0, "")
    return (70, 0, "")


def _category_node_id(category_code: str) -> str:
    return f"CATEGORY:{category_code}"


def _condition_node_id(fact_key: str) -> str:
    return f"CONDITION:{fact_key}"


def _policy_node_id(policy_id: str) -> str:
    return f"POLICY:{policy_id}"


def _action_node_id(policy_id: str) -> str:
    return f"ACTION:{policy_id}:review"


def _relation_edge_type(relation_type: str) -> str:
    normalized = relation_type.upper()
    if normalized in {"BEFORE", "AFTER", "REEVALUATE_AFTER"}:
        return "AVAILABLE_AFTER"
    return "RELATED"