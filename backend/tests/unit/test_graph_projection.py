import unittest

from app.modules.graph.projection import (
    GraphCategory,
    GraphEvaluation,
    GraphPolicy,
    GraphRelation,
    build_session_graph,
)


class GraphProjectionTests(unittest.TestCase):
    def test_builds_graph_from_facts_and_evaluations(self) -> None:
        graph = build_session_graph(
            facts={"region": "Seoul"},
            categories=[GraphCategory("housing", "Housing")],
            policies=[GraphPolicy("policy_housing_001", "housing", "Rent Support", "Seoul", "Grant")],
            evaluations=[
                GraphEvaluation(
                    "policy_housing_001",
                    "LIKELY_ELIGIBLE",
                    "ACTIVE",
                    1010,
                    {"satisfied": [{"factKey": "region", "ruleId": "rule_region", "required": True}]},
                )
            ],
            relations=[],
            selected_category_code="housing",
            selected_policy_id=None,
        )

        node_types = {node.type for node in graph.nodes}
        edge_types = {edge.type for edge in graph.edges}
        self.assertEqual({"USER", "CATEGORY", "CONDITION", "POLICY", "ACTION"}, node_types)
        self.assertIn("HAS_FACT", edge_types)
        self.assertIn("MATCHES", edge_types)
        self.assertIn("NEXT_ACTION", edge_types)

    def test_missing_and_failed_conditions_create_distinct_edges(self) -> None:
        graph = build_session_graph(
            facts={},
            categories=[GraphCategory("housing", "Housing")],
            policies=[GraphPolicy("policy_housing_001", "housing", "Rent Support", "Seoul", "Grant")],
            evaluations=[
                GraphEvaluation(
                    "policy_housing_001",
                    "NEEDS_CONFIRMATION",
                    "ACTIVE",
                    500,
                    {
                        "needsConfirmation": [{"factKey": "income", "ruleId": "rule_income"}],
                        "unsatisfied": [{"factKey": "region", "ruleId": "rule_region"}],
                    },
                )
            ],
            relations=[],
            selected_category_code="housing",
            selected_policy_id=None,
        )

        edge_types = {edge.type for edge in graph.edges}
        self.assertIn("MISSING_CONDITION", edge_types)
        self.assertIn("FAILED_CONDITION", edge_types)

    def test_selected_policy_centers_related_policy_graph(self) -> None:
        graph = build_session_graph(
            facts={},
            categories=[GraphCategory("housing", "Housing"), GraphCategory("loan", "Loan")],
            policies=[
                GraphPolicy("policy_housing_001", "housing", "Rent Support", "Seoul", "Grant"),
                GraphPolicy("policy_loan_001", "loan", "Loan Support", "National", "Loan"),
                GraphPolicy("policy_cash_001", "cash", "Cash Support", "Busan", "Cash"),
            ],
            evaluations=[],
            relations=[GraphRelation("rel_1", "policy_housing_001", "policy_loan_001", "RELATED")],
            selected_category_code=None,
            selected_policy_id="policy_housing_001",
        )

        node_ids = {node.id for node in graph.nodes}
        edge_types = {edge.type for edge in graph.edges}
        self.assertIn("policy:policy_housing_001", node_ids)
        self.assertIn("policy:policy_loan_001", node_ids)
        self.assertNotIn("policy:policy_cash_001", node_ids)
        self.assertIn("RELATED", edge_types)

    def test_node_limit_truncates_without_persisted_coordinates(self) -> None:
        policies = [
            GraphPolicy(f"policy_{index}", "housing", f"Policy {index}", "Seoul", "Grant")
            for index in range(10)
        ]

        graph = build_session_graph(
            facts={"region": "Seoul"},
            categories=[GraphCategory("housing", "Housing")],
            policies=policies,
            evaluations=[],
            relations=[],
            selected_category_code="housing",
            selected_policy_id=None,
            max_nodes=5,
        )

        self.assertEqual(graph.node_count, 5)
        self.assertTrue(graph.truncated)
        self.assertTrue(all("x" not in node.data and "y" not in node.data for node in graph.nodes))