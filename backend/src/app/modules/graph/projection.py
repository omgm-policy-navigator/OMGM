from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.graph.schemas import GraphEdgeResponse, GraphNodeResponse, SessionGraphResponse

DEFAULT_MAX_GRAPH_NODES = 80
MAX_GRAPH_NODES = 120
USER_NODE_ID = "user:anonymous"


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


@dataclass
class GraphBuilder:
    max_nodes: int
    nodes: dict[str, GraphNodeResponse] = field(default_factory=dict)
    edges: dict[str, GraphEdgeResponse] = field(default_factory=dict)
    truncated: bool = False

    def add_node(self, node_id: str, node_type: str, label: str, data: dict[str, Any] | None = None) -> bool:
        if node_id in self.nodes:
            return True
        if len(self.nodes) >= self.max_nodes:
            self.truncated = True
            return False
        self.nodes[node_id] = GraphNodeResponse(id=node_id, type=node_type, label=label, data=data or {})
        return True

    def add_edge(
        self,
        edge_id: str,
        edge_type: str,
        source: str,
        target: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        if edge_id in self.edges or source not in self.nodes or target not in self.nodes:
            return
        self.edges[edge_id] = GraphEdgeResponse(
            id=edge_id,
            type=edge_type,
            source=source,
            target=target,
            data=data or {},
        )

    def response(self) -> SessionGraphResponse:
        nodes = list(self.nodes.values())
        edges = list(self.edges.values())
        return SessionGraphResponse(
            nodes=nodes,
            edges=edges,
            nodeCount=len(nodes),
            edgeCount=len(edges),
            truncated=self.truncated,
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
    builder.add_node(USER_NODE_ID, "USER", "Anonymous user", {"factCount": len(facts)})

    category_by_code = {category.code: category for category in categories}
    policy_by_id = {policy.id: policy for policy in policies}
    evaluation_by_policy = {evaluation.policy_id: evaluation for evaluation in evaluations}
    visible_policy_ids = _visible_policy_ids(policies, relations, selected_category_code, selected_policy_id)

    for category in categories:
        if selected_category_code is not None and category.code != selected_category_code:
            continue
        category_node_id = _category_node_id(category.code)
        builder.add_node(category_node_id, "CATEGORY", category.name, {"categoryCode": category.code})
        builder.add_edge(f"selected:{category.code}", "SELECTED", USER_NODE_ID, category_node_id)

    for fact_key, value in sorted(facts.items()):
        fact_node_id = _condition_node_id(fact_key)
        builder.add_node(fact_node_id, "CONDITION", fact_key, {"factKey": fact_key, "value": value})
        builder.add_edge(f"has_fact:{fact_key}", "HAS_FACT", USER_NODE_ID, fact_node_id)

    sorted_policy_ids = sorted(
        visible_policy_ids,
        key=lambda policy_id: (
            -evaluation_by_policy.get(policy_id, _empty_evaluation(policy_id)).recommendation_score,
            policy_id,
        ),
    )
    for policy_id in sorted_policy_ids:
        policy = policy_by_id.get(policy_id)
        if policy is None:
            continue
        category = category_by_code.get(policy.category_code)
        policy_node_id = _policy_node_id(policy.id)
        evaluation = evaluation_by_policy.get(policy.id)
        if not builder.add_node(
            policy_node_id,
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
        ):
            break
        if category is not None:
            builder.add_node(
                _category_node_id(category.code),
                "CATEGORY",
                category.name,
                {"categoryCode": category.code},
            )
            builder.add_edge(
                f"category_policy:{category.code}:{policy.id}",
                "RECOMMENDS",
                _category_node_id(category.code),
                policy_node_id,
            )
        if evaluation is not None:
            _add_evaluation_edges(builder, evaluation, policy_node_id)
            action_node_id = _action_node_id(policy.id)
            builder.add_node(action_node_id, "ACTION", "Review application steps", {"policyId": policy.id})
            builder.add_edge(f"next_action:{policy.id}", "NEXT_ACTION", policy_node_id, action_node_id)

    for relation in relations:
        if relation.source_policy_id not in visible_policy_ids or relation.target_policy_id not in visible_policy_ids:
            continue
        source = _policy_node_id(relation.source_policy_id)
        target = _policy_node_id(relation.target_policy_id)
        edge_type = _relation_edge_type(relation.relation_type)
        builder.add_edge(
            f"relation:{relation.id}",
            edge_type,
            source,
            target,
            {"relationType": relation.relation_type},
        )

    return builder.response()


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
    centered = {selected_policy_id} if selected_policy_id in {policy.id for policy in policies} else set()
    for relation in relations:
        if relation.source_policy_id == selected_policy_id:
            centered.add(relation.target_policy_id)
        if relation.target_policy_id == selected_policy_id:
            centered.add(relation.source_policy_id)
    return centered & policy_ids if selected_category_code is not None else centered


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
            condition_node_id = _condition_node_id(str(fact_key))
            builder.add_node(condition_node_id, "CONDITION", str(fact_key), {"factKey": fact_key})
            builder.add_edge(
                f"{edge_type.lower()}:{fact_key}:{evaluation.policy_id}",
                edge_type,
                condition_node_id,
                policy_node_id,
                {"ruleId": item.get("ruleId"), "required": item.get("required")},
            )


def _empty_evaluation(policy_id: str) -> GraphEvaluation:
    return GraphEvaluation(policy_id, "", "", 0, {})


def _category_node_id(category_code: str) -> str:
    return f"category:{category_code}"


def _condition_node_id(fact_key: str) -> str:
    return f"condition:{fact_key}"


def _policy_node_id(policy_id: str) -> str:
    return f"policy:{policy_id}"


def _action_node_id(policy_id: str) -> str:
    return f"action:{policy_id}:review"


def _relation_edge_type(relation_type: str) -> str:
    normalized = relation_type.upper()
    if normalized in {"BEFORE", "AFTER", "REEVALUATE_AFTER"}:
        return "AVAILABLE_AFTER"
    return "RELATED"