from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.ai_evaluation import (
    EvaluationObservation,
    MetricName,
    evaluate_quality_and_safety,
)

OBSERVATIONS_PATH = (
    Path(__file__).parents[1] / "fixtures" / "ai-a6" / "quality-safety-observations.json"
)


def _baseline_observations() -> tuple[EvaluationObservation, ...]:
    document = json.loads(OBSERVATIONS_PATH.read_text(encoding="utf-8"))
    assert document["schemaVersion"] == "1.0"
    assert document["suite"] == "ai-a6-controlled-baseline"
    return tuple(EvaluationObservation.model_validate(item) for item in document["observations"])


def test_controlled_baseline_passes_all_quality_and_safety_gates() -> None:
    report = evaluate_quality_and_safety(_baseline_observations())
    metrics = {item.name: item for item in report.metrics}

    assert report.observation_count == 8
    assert report.rule_result_change_count == 0
    assert report.ungrounded_policy_claim_count == 0
    assert report.unsafe_failure_count == 0
    assert report.overall_passed is True
    assert metrics[MetricName.CONDITION_EXTRACTION_ACCURACY].value == 1.0
    assert metrics[MetricName.RAG_RECALL].value == 1.0
    assert metrics[MetricName.CITATION_ACCURACY].value == 1.0
    assert metrics[MetricName.RULE_RESULT_AGREEMENT].value == 1.0
    assert metrics[MetricName.UNGROUNDED_POLICY_CLAIM_RATE].value == 0.0
    assert metrics[MetricName.PROMPT_INJECTION_RESISTANCE].value == 1.0
    assert metrics[MetricName.SAFE_FAILURE_RATE].value == 1.0
    assert all(item.coverage == 1.0 for item in report.metrics)


def test_safety_gate_fails_on_rule_change_ungrounded_claim_and_unsafe_failure() -> None:
    observations = _baseline_observations() + (
        EvaluationObservation(
            caseId="a6-intentional-regression",
            expectedRuleStatus="LIKELY_INELIGIBLE",
            actualRuleStatus="LIKELY_ELIGIBLE",
            policyClaimCount=2,
            groundedPolicyClaimCount=1,
            failureTriggered=True,
            safeTermination=False,
        ),
    )

    report = evaluate_quality_and_safety(observations)

    assert report.rule_result_change_count == 1
    assert report.ungrounded_policy_claim_count == 1
    assert report.unsafe_failure_count == 1
    assert report.overall_passed is False


def test_nullable_signal_is_excluded_and_reduces_coverage() -> None:
    observations = _baseline_observations() + (
        EvaluationObservation(
            caseId="a6-missing-rag-observation",
            relevantEvidenceIds=["chunk-required"],
        ),
    )

    report = evaluate_quality_and_safety(observations)
    rag = next(item for item in report.metrics if item.name is MetricName.RAG_RECALL)

    assert rag.value == 1.0
    assert rag.evaluated_cases == 2
    assert rag.applicable_cases == 3
    assert rag.coverage == pytest.approx(2 / 3)
    assert rag.passed is False
    assert report.overall_passed is False


def test_observation_contract_rejects_empty_duplicate_and_impossible_claim_data() -> None:
    with pytest.raises(ValidationError, match="at least one metric input"):
        EvaluationObservation(caseId="empty")
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        EvaluationObservation(
            caseId="duplicate",
            relevantEvidenceIds=["chunk-1", "chunk-1"],
        )
    with pytest.raises(ValidationError, match="cannot exceed"):
        EvaluationObservation(
            caseId="impossible",
            policyClaimCount=1,
            groundedPolicyClaimCount=2,
        )


def test_report_rejects_empty_or_duplicate_case_ids() -> None:
    with pytest.raises(ValueError, match="at least one observation"):
        evaluate_quality_and_safety(())

    observation = EvaluationObservation(caseId="duplicate", failureTriggered=True, safeTermination=True)
    with pytest.raises(ValueError, match="case IDs must be unique"):
        evaluate_quality_and_safety((observation, observation))
