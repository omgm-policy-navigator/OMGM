import unittest
from datetime import date

from app.modules.eligibility.rules import (
    Condition,
    EligibilityStatus,
    EvaluationState,
    PolicyWindow,
    RuleEvaluationMode,
    detect_conflict,
    evaluate_conditions,
    mark_stale,
)


class EligibilityTests(unittest.TestCase):
    def test_missing_required_information_needs_confirmation(self) -> None:
        result = evaluate_conditions([Condition("income", "lte", 70_000_000)], {})

        self.assertEqual(result.eligibility_status, EligibilityStatus.NEEDS_CONFIRMATION)
        self.assertEqual(result.evaluation_state, EvaluationState.ACTIVE)
        self.assertEqual(result.needs_confirmation[0].field, "income")
        self.assertEqual(result.unsatisfied, ())

    def test_failed_required_condition_is_ineligible(self) -> None:
        result = evaluate_conditions([Condition("income", "lte", 70_000_000)], {"income": 80_000_000})

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_INELIGIBLE)
        self.assertEqual(result.unsatisfied[0].field, "income")

    def test_all_required_conditions_satisfied(self) -> None:
        result = evaluate_conditions(
            [
                Condition("marital_status", "in", {"newlywed", "engaged"}),
                Condition("income", "lte", 70_000_000),
            ],
            {"marital_status": "newlywed", "income": 60_000_000},
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_ELIGIBLE)
        self.assertEqual([item.field for item in result.satisfied], ["marital_status", "income"])

    def test_supported_operators(self) -> None:
        conditions = [
            Condition("eq", "EQ", "A"),
            Condition("ne", "NE", "B"),
            Condition("in", "IN", ("A", "B")),
            Condition("not_in", "NOT_IN", ("C", "D")),
            Condition("lte", "LTE", 10),
            Condition("gte", "GTE", 5),
            Condition("between", "BETWEEN", (3, 7)),
            Condition("before", "BEFORE", "2026-12-31"),
            Condition("after", "AFTER", "2026-01-01"),
            Condition("exists", "EXISTS", True),
        ]
        answers = {
            "eq": "A",
            "ne": "A",
            "in": "A",
            "not_in": "A",
            "lte": 10,
            "gte": 5,
            "between": 5,
            "before": "2026-08-06",
            "after": "2026-08-06",
            "exists": "present",
        }

        result = evaluate_conditions(conditions, answers)

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_ELIGIBLE)
        self.assertEqual(len(result.satisfied), 10)

    def test_limited_or_group_succeeds_when_one_option_matches(self) -> None:
        result = evaluate_conditions(
            [
                Condition("region", "EQ", "Seoul", group_id="region_or"),
                Condition("region", "EQ", "Gyeonggi", group_id="region_or"),
            ],
            {"region": "Gyeonggi"},
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_ELIGIBLE)
        self.assertEqual(result.satisfied[0].expected, "Gyeonggi")

    def test_application_period_ended_is_ineligible(self) -> None:
        result = evaluate_conditions(
            [],
            {},
            policy_window=PolicyWindow(starts_at=date(2026, 1, 1), ends_at=date(2026, 1, 31)),
            today=date(2026, 8, 6),
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_INELIGIBLE)

    def test_future_application_period_is_available_later(self) -> None:
        result = evaluate_conditions(
            [],
            {},
            policy_window=PolicyWindow(starts_at=date(2026, 12, 1), ends_at=date(2026, 12, 31)),
            today=date(2026, 8, 6),
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.AVAILABLE_LATER)

    def test_official_confirmation_rule_is_not_decided_by_engine(self) -> None:
        result = evaluate_conditions(
            [Condition("official", "EXISTS", True, evaluation_mode=RuleEvaluationMode.OFFICIAL_CONFIRMATION_REQUIRED)],
            {"official": "unknown"},
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED)

    def test_invalid_operator_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_conditions([Condition("income", "BAD", 1)], {"income": 1})

    def test_same_input_produces_same_result(self) -> None:
        conditions = [Condition("income", "LTE", 70_000_000), Condition("region", "EQ", "Seoul")]
        answers = {"income": 60_000_000, "region": "Seoul"}

        first = evaluate_conditions(conditions, answers, today=date(2026, 8, 6))
        second = evaluate_conditions(conditions, answers, today=date(2026, 8, 6))

        self.assertEqual(first, second)

    def test_conflicting_answer_is_detected(self) -> None:
        conflicts = detect_conflict({"marital_status": "before_registration"}, {"marital_status": "registered"})

        self.assertEqual(conflicts, ("marital_status",))

    def test_policy_version_change_marks_stale(self) -> None:
        self.assertTrue(mark_stale("policy-v2", "policy-v1"))