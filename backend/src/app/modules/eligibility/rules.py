from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EligibilityStatus(StrEnum):
    LIKELY_ELIGIBLE = "LIKELY_ELIGIBLE"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    AVAILABLE_LATER = "AVAILABLE_LATER"
    LIKELY_INELIGIBLE = "LIKELY_INELIGIBLE"
    OFFICIAL_CONFIRMATION_REQUIRED = "OFFICIAL_CONFIRMATION_REQUIRED"


class EvaluationState(StrEnum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class Condition:
    field: str
    operator: str
    expected: Any
    required: bool = True


@dataclass(frozen=True)
class EvaluationResult:
    eligibility_status: EligibilityStatus
    evaluation_state: EvaluationState = EvaluationState.ACTIVE
    satisfied: tuple[str, ...] = ()
    unsatisfied: tuple[str, ...] = ()
    needs_confirmation: tuple[str, ...] = ()


def evaluate_conditions(conditions: list[Condition], answers: dict[str, Any]) -> EvaluationResult:
    satisfied: list[str] = []
    unsatisfied: list[str] = []
    needs_confirmation: list[str] = []

    for condition in conditions:
        value = answers.get(condition.field)
        if value is None or value == "":
            if condition.required:
                needs_confirmation.append(condition.field)
            continue

        if _compare(value, condition.operator, condition.expected):
            satisfied.append(condition.field)
        elif condition.required:
            unsatisfied.append(condition.field)

    if needs_confirmation:
        return EvaluationResult(
            eligibility_status=EligibilityStatus.NEEDS_CONFIRMATION,
            evaluation_state=EvaluationState.ACTIVE,
            satisfied=tuple(satisfied),
            unsatisfied=tuple(unsatisfied),
            needs_confirmation=tuple(needs_confirmation),
        )
    if unsatisfied:
        return EvaluationResult(
            eligibility_status=EligibilityStatus.LIKELY_INELIGIBLE,
            evaluation_state=EvaluationState.ACTIVE,
            satisfied=tuple(satisfied),
            unsatisfied=tuple(unsatisfied),
        )
    return EvaluationResult(
        eligibility_status=EligibilityStatus.LIKELY_ELIGIBLE,
        evaluation_state=EvaluationState.ACTIVE,
        satisfied=tuple(satisfied),
    )


def mark_stale(current_policy_version: str, evaluated_policy_version: str) -> bool:
    return current_policy_version != evaluated_policy_version


def detect_conflict(previous: dict[str, Any], incoming: dict[str, Any]) -> tuple[str, ...]:
    conflicts = []
    for field, new_value in incoming.items():
        if field in previous and previous[field] not in (None, "") and previous[field] != new_value:
            conflicts.append(field)
    return tuple(conflicts)


def _compare(value: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        return value == expected
    if operator == "lte":
        return value <= expected
    if operator == "gte":
        return value >= expected
    if operator == "in":
        return value in expected
    raise ValueError(f"Unsupported operator: {operator}")
