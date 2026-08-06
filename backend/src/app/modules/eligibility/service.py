from __future__ import annotations

from datetime import date
from typing import Any

from app.catalog.models import Policy, PolicyEvaluation, PolicyRule
from app.modules.eligibility.rules import Condition, EvaluationResult, PolicyWindow, evaluate_conditions
from app.modules.eligibility.schemas import EvaluationEvidenceResponse, PolicyEvaluationResponse


def condition_from_policy_rule(rule: PolicyRule) -> Condition:
    operator = rule.operator.upper()
    expected = parse_expected_value(rule.value_text, operator)
    if rule.fact_key == "region" and str(rule.value_text).strip().lower() == "national":
        operator = "EXISTS"
        expected = True
    return Condition(
        field=rule.fact_key,
        operator=operator,
        expected=expected,
        required=rule.required,
        rule_id=rule.id,
        evidence=rule.evidence_text,
    )


def evaluate_policy(policy: Policy, facts: dict[str, Any], *, today: date | None = None) -> EvaluationResult:
    return evaluate_conditions(
        [condition_from_policy_rule(rule) for rule in policy.rules],
        facts,
        policy_window=parse_application_period(policy.application_period),
        today=today,
    )


def evidence_from_result(result: EvaluationResult) -> dict[str, list[dict[str, Any]]]:
    return {
        "satisfied": [_condition_evidence_to_dict(item) for item in result.satisfied],
        "unsatisfied": [_condition_evidence_to_dict(item) for item in result.unsatisfied],
        "needsConfirmation": [_condition_evidence_to_dict(item) for item in result.needs_confirmation],
        "officialConfirmationRequired": [
            _condition_evidence_to_dict(item) for item in result.official_confirmation_required
        ],
    }


def evaluation_to_response(evaluation: PolicyEvaluation) -> PolicyEvaluationResponse:
    return PolicyEvaluationResponse(
        policyId=evaluation.policy_id,
        eligibilityStatus=evaluation.eligibility_status,
        evaluationState=evaluation.evaluation_state,
        recommendationScore=evaluation.recommendation_score,
        evidence=EvaluationEvidenceResponse.model_validate(evaluation.evidence),
        evaluatedAt=evaluation.evaluated_at.isoformat(),
        updatedAt=evaluation.updated_at.isoformat(),
    )


def parse_expected_value(value_text: str, operator: str) -> Any:
    text = value_text.strip()
    normalized = operator.upper()
    if normalized in {"IN", "NOT_IN", "BETWEEN"}:
        return tuple(part.strip() for part in text.split("|") if part.strip())
    if normalized in {"LTE", "GTE"}:
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text
    return text


def parse_application_period(application_period: str) -> PolicyWindow:
    parts = [part.strip() for part in application_period.split(" to ")]
    if len(parts) != 2:
        return PolicyWindow()
    return PolicyWindow(starts_at=_parse_date(parts[0]), ends_at=_parse_date(parts[1]))


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _condition_evidence_to_dict(item) -> dict[str, Any]:
    return {
        "ruleId": item.rule_id,
        "factKey": item.field,
        "operator": item.operator.upper(),
        "expected": item.expected,
        "actual": item.actual,
        "required": item.required,
        "evidence": item.evidence,
    }