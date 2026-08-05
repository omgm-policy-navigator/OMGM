import unittest

from app.eligibility.rules import (
    Condition,
    EligibilityStatus,
    detect_conflict,
    evaluate_conditions,
    mark_stale,
)


class EligibilityTests(unittest.TestCase):
    def test_missing_required_information_needs_confirmation(self) -> None:
        result = evaluate_conditions([Condition("income", "lte", 70_000_000)], {})

        self.assertEqual(result.status, EligibilityStatus.NEEDS_CONFIRMATION)
        self.assertEqual(result.needs_confirmation, ("income",))
        self.assertEqual(result.unsatisfied, ())

    def test_failed_required_condition_is_ineligible(self) -> None:
        result = evaluate_conditions(
            [Condition("income", "lte", 70_000_000)],
            {"income": 80_000_000},
        )

        self.assertEqual(result.status, EligibilityStatus.INELIGIBLE)
        self.assertEqual(result.unsatisfied, ("income",))

    def test_all_required_conditions_satisfied(self) -> None:
        result = evaluate_conditions(
            [
                Condition("marital_status", "in", {"newlywed", "engaged"}),
                Condition("income", "lte", 70_000_000),
            ],
            {"marital_status": "newlywed", "income": 60_000_000},
        )

        self.assertEqual(result.status, EligibilityStatus.ELIGIBLE)

    def test_conflicting_answer_is_detected(self) -> None:
        conflicts = detect_conflict(
            {"marital_status": "before_registration"},
            {"marital_status": "registered"},
        )

        self.assertEqual(conflicts, ("marital_status",))

    def test_policy_version_change_marks_stale(self) -> None:
        self.assertTrue(mark_stale("policy-v2", "policy-v1"))
