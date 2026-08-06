from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


class RuleOperator(StrEnum):
    EQ = "EQ"
    NE = "NE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    LTE = "LTE"
    GTE = "GTE"
    BETWEEN = "BETWEEN"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    EXISTS = "EXISTS"


class RuleEvaluationMode(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    OFFICIAL_CONFIRMATION_REQUIRED = "OFFICIAL_CONFIRMATION_REQUIRED"


@dataclass(frozen=True)
class Condition:
    field: str
    operator: str
    expected: Any
    required: bool = True
    rule_id: str | None = None
    evidence: str | None = None
    group_id: str | None = None
    evaluation_mode: RuleEvaluationMode = RuleEvaluationMode.DETERMINISTIC


@dataclass(frozen=True)
class PolicyWindow:
    starts_at: date | None = None
    ends_at: date | None = None


@dataclass(frozen=True)
class ConditionEvidence:
    rule_id: str | None
    field: str
    operator: str
    expected: Any
    actual: Any
    required: bool
    evidence: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    eligibility_status: EligibilityStatus
    evaluation_state: EvaluationState = EvaluationState.ACTIVE
    satisfied: tuple[ConditionEvidence, ...] = ()
    unsatisfied: tuple[ConditionEvidence, ...] = ()
    needs_confirmation: tuple[ConditionEvidence, ...] = ()
    official_confirmation_required: tuple[ConditionEvidence, ...] = ()
    recommendation_score: int = 0


def evaluate_conditions(
    conditions: list[Condition],
    answers: dict[str, Any],
    *,
    policy_window: PolicyWindow | None = None,
    today: date | None = None,
) -> EvaluationResult:
    current_date = today or date.today()
    if policy_window is not None:
        if policy_window.ends_at is not None and current_date > policy_window.ends_at:
            return EvaluationResult(eligibility_status=EligibilityStatus.LIKELY_INELIGIBLE, recommendation_score=-1000)
        if policy_window.starts_at is not None and current_date < policy_window.starts_at:
            return EvaluationResult(eligibility_status=EligibilityStatus.AVAILABLE_LATER, recommendation_score=-100)

    satisfied: list[ConditionEvidence] = []
    unsatisfied: list[ConditionEvidence] = []
    needs_confirmation: list[ConditionEvidence] = []
    official_confirmation: list[ConditionEvidence] = []

    for group in _group_conditions(conditions):
        result = _evaluate_condition_group(group, answers)
        satisfied.extend(result.satisfied)
        unsatisfied.extend(result.unsatisfied)
        needs_confirmation.extend(result.needs_confirmation)
        official_confirmation.extend(result.official_confirmation_required)

    if unsatisfied:
        status = EligibilityStatus.LIKELY_INELIGIBLE
    elif needs_confirmation:
        status = EligibilityStatus.NEEDS_CONFIRMATION
    elif official_confirmation:
        status = EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED
    else:
        status = EligibilityStatus.LIKELY_ELIGIBLE

    return EvaluationResult(
        eligibility_status=status,
        evaluation_state=EvaluationState.ACTIVE,
        satisfied=tuple(satisfied),
        unsatisfied=tuple(unsatisfied),
        needs_confirmation=tuple(needs_confirmation),
        official_confirmation_required=tuple(official_confirmation),
        recommendation_score=_score(status, satisfied, unsatisfied, needs_confirmation, official_confirmation),
    )


def mark_stale(current_policy_version: str, evaluated_policy_version: str) -> bool:
    return current_policy_version != evaluated_policy_version


def detect_conflict(previous: dict[str, Any], incoming: dict[str, Any]) -> tuple[str, ...]:
    conflicts = []
    for field, new_value in incoming.items():
        if field in previous and previous[field] not in (None, "") and previous[field] != new_value:
            conflicts.append(field)
    return tuple(conflicts)


@dataclass(frozen=True)
class _GroupResult:
    satisfied: tuple[ConditionEvidence, ...] = ()
    unsatisfied: tuple[ConditionEvidence, ...] = ()
    needs_confirmation: tuple[ConditionEvidence, ...] = ()
    official_confirmation_required: tuple[ConditionEvidence, ...] = ()


def _group_conditions(conditions: list[Condition]) -> list[list[Condition]]:
    groups: dict[str, list[Condition]] = {}
    standalone: list[list[Condition]] = []
    for condition in conditions:
        if condition.group_id is None:
            standalone.append([condition])
        else:
            groups.setdefault(condition.group_id, []).append(condition)
    return standalone + list(groups.values())


def _evaluate_condition_group(group: list[Condition], answers: dict[str, Any]) -> _GroupResult:
    results = [_evaluate_single(condition, answers) for condition in group]
    if len(group) == 1:
        return results[0]
    if any(result.satisfied for result in results):
        satisfied = tuple(item for result in results for item in result.satisfied)
        return _GroupResult(satisfied=satisfied)
    if any(result.needs_confirmation for result in results):
        needs = tuple(item for result in results for item in result.needs_confirmation)
        return _GroupResult(needs_confirmation=needs)
    unsatisfied = tuple(item for result in results for item in result.unsatisfied)
    return _GroupResult(unsatisfied=unsatisfied)


def _evaluate_single(condition: Condition, answers: dict[str, Any]) -> _GroupResult:
    actual = answers.get(condition.field)
    evidence = ConditionEvidence(
        rule_id=condition.rule_id,
        field=condition.field,
        operator=condition.operator,
        expected=condition.expected,
        actual=actual,
        required=condition.required,
        evidence=condition.evidence,
    )
    if condition.evaluation_mode is RuleEvaluationMode.OFFICIAL_CONFIRMATION_REQUIRED:
        return _GroupResult(official_confirmation_required=(evidence,))
    if actual is None or actual == "":
        if condition.required:
            return _GroupResult(needs_confirmation=(evidence,))
        return _GroupResult()
    if _compare(actual, condition.operator, condition.expected):
        return _GroupResult(satisfied=(evidence,))
    if condition.required:
        return _GroupResult(unsatisfied=(evidence,))
    return _GroupResult()


def _score(
    status: EligibilityStatus,
    satisfied: list[ConditionEvidence],
    unsatisfied: list[ConditionEvidence],
    needs_confirmation: list[ConditionEvidence],
    official_confirmation: list[ConditionEvidence],
) -> int:
    base = {
        EligibilityStatus.LIKELY_ELIGIBLE: 1000,
        EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED: 850,
        EligibilityStatus.NEEDS_CONFIRMATION: 600,
        EligibilityStatus.AVAILABLE_LATER: 400,
        EligibilityStatus.LIKELY_INELIGIBLE: 0,
    }[status]
    return (
        base
        + len(satisfied) * 10
        - len(needs_confirmation) * 5
        - len(official_confirmation) * 3
        - len(unsatisfied) * 50
    )


def _compare(value: Any, operator: str, expected: Any) -> bool:
    normalized = operator.upper()
    try:
        parsed_operator = RuleOperator(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported operator: {operator}") from exc

    if parsed_operator is RuleOperator.EQ:
        return value == expected
    if parsed_operator is RuleOperator.NE:
        return value != expected
    if parsed_operator is RuleOperator.IN:
        return value in _as_collection(expected)
    if parsed_operator is RuleOperator.NOT_IN:
        return value not in _as_collection(expected)
    if parsed_operator is RuleOperator.LTE:
        return _coerce_comparable(value) <= _coerce_comparable(expected)
    if parsed_operator is RuleOperator.GTE:
        return _coerce_comparable(value) >= _coerce_comparable(expected)
    if parsed_operator is RuleOperator.BETWEEN:
        lower, upper = _between_bounds(expected)
        coerced = _coerce_comparable(value)
        return _coerce_comparable(lower) <= coerced <= _coerce_comparable(upper)
    if parsed_operator is RuleOperator.BEFORE:
        return _coerce_comparable(value) < _coerce_comparable(expected)
    if parsed_operator is RuleOperator.AFTER:
        return _coerce_comparable(value) > _coerce_comparable(expected)
    if parsed_operator is RuleOperator.EXISTS:
        return value is not None and value != ""
    raise ValueError(f"Unsupported operator: {operator}")


def _as_collection(expected: Any) -> tuple[Any, ...]:
    if isinstance(expected, str):
        return tuple(part.strip() for part in expected.split("|") if part.strip())
    if isinstance(expected, list | tuple | set):
        return tuple(expected)
    return (expected,)


def _between_bounds(expected: Any) -> tuple[Any, Any]:
    values = _as_collection(expected)
    if len(values) != 2:
        raise ValueError("BETWEEN expected value must contain exactly two bounds")
    return values[0], values[1]


def _coerce_comparable(value: Any) -> Any:
    if isinstance(value, int | float | date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return value