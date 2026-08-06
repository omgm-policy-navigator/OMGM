import unittest
from datetime import UTC, date, datetime

from app.modules.eligibility.rules import (
    Condition,
    ConditionGroup,
    ConditionResult,
    EligibilityStatus,
    EvaluationState,
    GroupOperator,
    PolicyWindow,
    RuleEvaluationMode,
    detect_conflict,
    evaluate_condition_group,
    evaluate_conditions,
    mark_stale,
)


class EligibilityTests(unittest.TestCase):
    def test_missing_required_information_needs_confirmation(self) -> None:
        result = evaluate_conditions([Condition("income", "lte", 70_000_000)], {})

        self.assertEqual(result.eligibility_status, EligibilityStatus.NEEDS_CONFIRMATION)
        self.assertEqual(result.evaluation_state, EvaluationState.ACTIVE)
        self.assertEqual(result.needs_confirmation[0].field, "income")
        self.assertEqual(result.needs_confirmation[0].result, ConditionResult.UNKNOWN)
        self.assertEqual(result.unsatisfied, ())

    def test_failed_required_condition_is_ineligible(self) -> None:
        result = evaluate_conditions([Condition("income", "lte", 70_000_000)], {"income": 80_000_000})

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_INELIGIBLE)
        self.assertEqual(result.unsatisfied[0].field, "income")
        self.assertEqual(result.unsatisfied[0].result, ConditionResult.UNMET)

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


    def test_unknown_required_condition_takes_precedence_over_falsey_missing_values(self) -> None:
        result = evaluate_conditions(
            [Condition("income", "LTE", 70_000_000), Condition("region", "EQ", "Seoul")],
            {"region": "Seoul"},
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.NEEDS_CONFIRMATION)
        self.assertEqual(result.needs_confirmation[0].result, ConditionResult.UNKNOWN)
        self.assertEqual(result.unsatisfied, ())

    def test_unmet_required_condition_overrides_unknown_required_condition(self) -> None:
        result = evaluate_conditions(
            [Condition("income", "LTE", 70_000_000), Condition("region", "EQ", "Seoul")],
            {"income": 80_000_000},
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_INELIGIBLE)
        self.assertEqual(result.unsatisfied[0].result, ConditionResult.UNMET)
        self.assertEqual(result.needs_confirmation[0].result, ConditionResult.UNKNOWN)
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


    def test_explicit_group_object_evaluates_and_with_nested_or(self) -> None:
        group = ConditionGroup(
            GroupOperator.AND,
            (
                Condition("income", "LTE", 60_000_000),
                ConditionGroup(
                    GroupOperator.OR,
                    (
                        Condition("children_count", "GTE", 2),
                        Condition("is_multicultural", "EQ", True),
                    ),
                ),
            ),
        )

        result = evaluate_condition_group(group, {"income": 55_000_000, "is_multicultural": True})

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_ELIGIBLE)
        self.assertEqual([item.field for item in result.satisfied], ["income", "is_multicultural"])

    def test_explicit_or_group_with_only_unknown_children_needs_confirmation(self) -> None:
        group = ConditionGroup(
            GroupOperator.AND,
            (
                Condition("income", "LTE", 60_000_000),
                ConditionGroup(
                    GroupOperator.OR,
                    (
                        Condition("children_count", "GTE", 2),
                        Condition("is_multicultural", "EQ", True),
                    ),
                ),
            ),
        )

        result = evaluate_condition_group(group, {"income": 55_000_000})

        self.assertEqual(result.eligibility_status, EligibilityStatus.NEEDS_CONFIRMATION)
        self.assertEqual({item.field for item in result.needs_confirmation}, {"children_count", "is_multicultural"})

    def test_evaluation_time_accepts_timezone_aware_datetime(self) -> None:
        result = evaluate_conditions(
            [],
            {},
            policy_window=PolicyWindow(starts_at=date(2026, 8, 6), ends_at=date(2026, 8, 6)),
            evaluation_time=datetime(2026, 8, 6, 23, 30, tzinfo=UTC),
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_ELIGIBLE)

    def test_iso_datetime_comparison_is_timezone_safe(self) -> None:
        result = evaluate_conditions(
            [Condition("submitted_at", "BEFORE", "2026-08-07T00:00:00+00:00")],
            {"submitted_at": "2026-08-06T23:00:00Z"},
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_ELIGIBLE)
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


    def test_date_and_iso_datetime_comparison_uses_stable_timezone_normalization(self) -> None:
        result = evaluate_conditions(
            [Condition("submitted_at", "AFTER", "2026-08-06")],
            {"submitted_at": "2026-08-06T01:00:00+00:00"},
        )

        self.assertEqual(result.eligibility_status, EligibilityStatus.LIKELY_ELIGIBLE)
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
