from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
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


class ConditionResult(StrEnum):
    MET = "MET"
    UNMET = "UNMET"
    UNKNOWN = "UNKNOWN"
    OFFICIAL_CONFIRMATION_REQUIRED = "OFFICIAL_CONFIRMATION_REQUIRED"


class GroupOperator(StrEnum):
    AND = "AND"
    OR = "OR"


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
class ConditionGroup:
    operator: GroupOperator
    conditions: tuple[Condition | ConditionGroup, ...]


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
    result: ConditionResult
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
    evaluation_time: date | datetime | None = None,
) -> EvaluationResult:
    current_date = _evaluation_date(evaluation_time or today)
    if policy_window is not None:
        if policy_window.ends_at is not None and current_date > policy_window.ends_at:
            return EvaluationResult(eligibility_status=EligibilityStatus.LIKELY_INELIGIBLE, recommendation_score=-1000)
        if policy_window.starts_at is not None and current_date < policy_window.starts_at:
            return EvaluationResult(eligibility_status=EligibilityStatus.AVAILABLE_LATER, recommendation_score=-100)

    return evaluate_condition_group(_legacy_conditions_to_group(conditions), answers)


def evaluate_condition_group(group: ConditionGroup, answers: dict[str, Any]) -> EvaluationResult:
    result = _evaluate_group(group, answers)
    status = _status_from_evidence(
        result.unsatisfied,
        result.needs_confirmation,
        result.official_confirmation_required,
    )
    satisfied = list(result.satisfied)
    unsatisfied = list(result.unsatisfied)
    needs_confirmation = list(result.needs_confirmation)
    official_confirmation = list(result.official_confirmation_required)
    return EvaluationResult(
        eligibility_status=status,
        evaluation_state=EvaluationState.ACTIVE,
        satisfied=result.satisfied,
        unsatisfied=result.unsatisfied,
        needs_confirmation=result.needs_confirmation,
        official_confirmation_required=result.official_confirmation_required,
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

    @property
    def condition_result(self) -> ConditionResult:
        if self.unsatisfied:
            return ConditionResult.UNMET
        if self.needs_confirmation:
            return ConditionResult.UNKNOWN
        if self.official_confirmation_required:
            return ConditionResult.OFFICIAL_CONFIRMATION_REQUIRED
        return ConditionResult.MET


def _legacy_conditions_to_group(conditions: list[Condition]) -> ConditionGroup:
    groups: dict[str, list[Condition]] = {}
    top_level: list[Condition | ConditionGroup] = []
    for condition in conditions:
        if condition.group_id is None:
            top_level.append(condition)
        else:
            groups.setdefault(condition.group_id, []).append(condition)
    top_level.extend(ConditionGroup(GroupOperator.OR, tuple(group)) for group in groups.values())
    return ConditionGroup(GroupOperator.AND, tuple(top_level))


def _evaluate_group(group: ConditionGroup, answers: dict[str, Any]) -> _GroupResult:
    results = [
        _evaluate_group(item, answers) if isinstance(item, ConditionGroup) else _evaluate_single(item, answers)
        for item in group.conditions
    ]
    if group.operator is GroupOperator.AND:
        return _merge_and(results)
    if group.operator is GroupOperator.OR:
        return _merge_or(results)
    raise ValueError(f"Unsupported group operator: {group.operator}")


def _merge_and(results: list[_GroupResult]) -> _GroupResult:
    return _GroupResult(
        satisfied=tuple(item for result in results for item in result.satisfied),
        unsatisfied=tuple(item for result in results for item in result.unsatisfied),
        needs_confirmation=tuple(item for result in results for item in result.needs_confirmation),
        official_confirmation_required=tuple(
            item for result in results for item in result.official_confirmation_required
        ),
    )


def _merge_or(results: list[_GroupResult]) -> _GroupResult:
    met_results = [result for result in results if result.condition_result is ConditionResult.MET]
    if met_results:
        return _GroupResult(satisfied=tuple(item for result in met_results for item in result.satisfied))
    unknown_results = [result for result in results if result.condition_result is ConditionResult.UNKNOWN]
    if unknown_results:
        return _GroupResult(
            needs_confirmation=tuple(item for result in unknown_results for item in result.needs_confirmation)
        )
    official_results = [
        result for result in results if result.condition_result is ConditionResult.OFFICIAL_CONFIRMATION_REQUIRED
    ]
    if official_results:
        return _GroupResult(
            official_confirmation_required=tuple(
                item for result in official_results for item in result.official_confirmation_required
            )
        )
    return _GroupResult(unsatisfied=tuple(item for result in results for item in result.unsatisfied))


def _evaluate_single(condition: Condition, answers: dict[str, Any]) -> _GroupResult:
    actual = answers.get(condition.field)
    if condition.evaluation_mode is RuleEvaluationMode.OFFICIAL_CONFIRMATION_REQUIRED:
        evidence = _condition_evidence(condition, actual, ConditionResult.OFFICIAL_CONFIRMATION_REQUIRED)
        return _GroupResult(official_confirmation_required=(evidence,))
    if actual is None or actual == "":
        if condition.required:
            evidence = _condition_evidence(condition, actual, ConditionResult.UNKNOWN)
            return _GroupResult(needs_confirmation=(evidence,))
        return _GroupResult()
    if _compare(actual, condition.operator, condition.expected):
        evidence = _condition_evidence(condition, actual, ConditionResult.MET)
        return _GroupResult(satisfied=(evidence,))
    if condition.required:
        evidence = _condition_evidence(condition, actual, ConditionResult.UNMET)
        return _GroupResult(unsatisfied=(evidence,))
    return _GroupResult()


def _condition_evidence(condition: Condition, actual: Any, result: ConditionResult) -> ConditionEvidence:
    return ConditionEvidence(
        rule_id=condition.rule_id,
        field=condition.field,
        operator=condition.operator,
        expected=condition.expected,
        actual=actual,
        required=condition.required,
        result=result,
        evidence=condition.evidence,
    )


def _status_from_evidence(
    unsatisfied: tuple[ConditionEvidence, ...],
    needs_confirmation: tuple[ConditionEvidence, ...],
    official_confirmation: tuple[ConditionEvidence, ...],
) -> EligibilityStatus:
    if unsatisfied:
        return EligibilityStatus.LIKELY_INELIGIBLE
    if needs_confirmation:
        return EligibilityStatus.NEEDS_CONFIRMATION
    if official_confirmation:
        return EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED
    return EligibilityStatus.LIKELY_ELIGIBLE


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
        left, right = _coerce_ordered_pair(value, expected)
        return left <= right
    if parsed_operator is RuleOperator.GTE:
        left, right = _coerce_ordered_pair(value, expected)
        return left >= right
    if parsed_operator is RuleOperator.BETWEEN:
        lower, upper = _between_bounds(expected)
        lower_bound, coerced = _coerce_ordered_pair(lower, value)
        coerced, upper_bound = _coerce_ordered_pair(coerced, upper)
        return lower_bound <= coerced <= upper_bound
    if parsed_operator is RuleOperator.BEFORE:
        left, right = _coerce_ordered_pair(value, expected)
        return left < right
    if parsed_operator is RuleOperator.AFTER:
        left, right = _coerce_ordered_pair(value, expected)
        return left > right
    if parsed_operator is RuleOperator.EXISTS:
        return value is not None and value != ""
    raise ValueError(f"Unsupported operator: {operator}")


def _evaluation_date(value: date | datetime | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).date()
        return value.date()
    return value


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


def _coerce_ordered_pair(left: Any, right: Any) -> tuple[Any, Any]:
    coerced_left = _coerce_comparable(left)
    coerced_right = _coerce_comparable(right)
    if (
        isinstance(coerced_left, datetime)
        and isinstance(coerced_right, date)
        and not isinstance(coerced_right, datetime)
    ):
        coerced_right = datetime.combine(coerced_right, datetime.min.time(), tzinfo=coerced_left.tzinfo)
    if (
        isinstance(coerced_right, datetime)
        and isinstance(coerced_left, date)
        and not isinstance(coerced_left, datetime)
    ):
        coerced_left = datetime.combine(coerced_left, datetime.min.time(), tzinfo=coerced_right.tzinfo)
    if isinstance(coerced_left, datetime) and isinstance(coerced_right, datetime):
        if coerced_left.tzinfo is not None and coerced_right.tzinfo is None:
            coerced_right = coerced_right.replace(tzinfo=UTC)
        if coerced_right.tzinfo is not None and coerced_left.tzinfo is None:
            coerced_left = coerced_left.replace(tzinfo=UTC)
    return coerced_left, coerced_right


def _coerce_comparable(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC)
        return value
    if isinstance(value, int | float | date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return date.fromisoformat(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value
    return value
