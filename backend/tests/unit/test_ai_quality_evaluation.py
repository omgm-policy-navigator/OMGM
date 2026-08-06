from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.llm.fake import FakeLLMProvider
from app.llm.schemas import AIOutput
from app.modules.ai_evaluation import (
    EvaluationObservation,
    MetricName,
    MetricStatus,
    evaluate_quality_and_safety,
    validate_a6_baseline,
)
from app.modules.eligibility.rules import Condition, evaluate_conditions
from app.modules.explanations import (
    ExplanationStatus,
    GroundedAnswerInput,
    UserConditionContext,
    generate_rule_grounded_answer,
)
from app.modules.rag.search import SearchHit, search_policy_evidence
from app.modules.user_facts.extraction import (
    parse_condition_extraction,
    review_condition_extraction,
)

OBSERVATIONS_PATH = (
    Path(__file__).parents[1] / "fixtures" / "ai-a6" / "quality-safety-observations.json"
)


class _EmbeddingProvider:
    model = "qwen3-embedding:0.6b"

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((0.1,) for _ in texts)


class _RagRepository:
    def __init__(self, hits: tuple[SearchHit, ...]) -> None:
        self.hits = hits

    async def search(self, **_: object) -> tuple[SearchHit, ...]:
        return self.hits


class _FailingProvider(FakeLLMProvider):
    async def generate(self, request: object) -> AIOutput:
        raise TimeoutError("controlled timeout")


def _baseline_observations() -> tuple[EvaluationObservation, ...]:
    document = json.loads(OBSERVATIONS_PATH.read_text(encoding="utf-8"))
    assert document["schemaVersion"] == "1.1"
    assert document["suite"] == "ai-a6-controlled-baseline"
    cases = {item["caseId"]: item for item in document["cases"]}
    happy = cases["a6-grounded-eligible"]
    payload = happy["input"]
    expected = happy["expected"]

    extraction = parse_condition_extraction(
        json.dumps({"candidates": payload["modelCandidates"]}, ensure_ascii=False)
    )
    reviewed = review_condition_extraction(extraction, payload["userText"])
    actual_facts = {item.fact_key.value: item.raw_value for item in reviewed.candidates}
    conditions = [
        Condition(
            rule_id=item["ruleId"],
            field=item["field"],
            operator=item["operator"],
            expected=item["expected"],
            required=item["required"],
        )
        for item in payload["conditions"]
    ]
    evaluation = evaluate_conditions(conditions, actual_facts)
    hits = tuple(
        SearchHit(
            chunk_id=item["chunkId"],
            document_id=item["documentId"],
            policy_id=item["policyId"],
            policy_version=item["policyVersion"],
            title=item["title"],
            content=item["content"],
            source_url=item["sourceUrl"],
            source_location=item["sourceLocation"],
            chunk_type=item["chunkType"],
            similarity=item["similarity"],
        )
        for item in payload["ragHits"]
    )
    rag = asyncio.run(
        search_policy_evidence(
            policy_id="policy-1",
            question="신청할 수 있나요?",
            provider=_EmbeddingProvider(),
            repository=_RagRepository(hits),
        )
    )
    grounded_input = GroundedAnswerInput(
        user_question="신청할 수 있나요?",
        user_conditions=tuple(
            UserConditionContext(key=key, value=value) for key, value in actual_facts.items()
        ),
        evaluation=evaluation,
        citations=rag.citations,
    )
    provider_output = AIOutput(
        answer="공식 근거 설명",
        resultStatus="ANSWERED",
        matchedConditions=[
            {"conditionId": item.rule_id, "label": item.field} for item in evaluation.satisfied
        ],
        citations=[
            {
                "sourceId": item.source_id,
                "evidenceId": item.evidence_id,
                "policyVersionId": item.policy_version_id,
                "title": item.title,
                "url": item.url,
                "excerpt": item.excerpt,
            }
            for item in rag.citations
        ],
    )
    grounded_answer = asyncio.run(
        generate_rule_grounded_answer(
            grounded_input, FakeLLMProvider(output=provider_output)
        )
    )
    observations = [
        EvaluationObservation(
            caseId=happy["caseId"],
            expectedFacts=expected["facts"],
            actualFacts=actual_facts,
            relevantEvidenceIds=expected["relevantEvidenceIds"],
            retrievedEvidenceIds=[item.evidence_id for item in rag.citations],
            allowedCitationIds=expected["allowedCitationIds"],
            requiredCitationIds=expected["requiredCitationIds"],
            actualCitationIds=[item.evidence_id for item in grounded_answer.official_sources],
            expectedRuleStatus=expected["ruleStatus"],
            actualRuleStatus=evaluation.eligibility_status.value,
            policyClaimCount=expected["policyClaimCount"],
            groundedPolicyClaimCount=len(grounded_answer.official_sources),
        )
    ]
    observations.extend(_failure_observations(cases, grounded_input, provider_output))
    return tuple(observations)


def _failure_observations(
    cases: dict[str, dict[str, Any]],
    grounded_input: GroundedAnswerInput,
    provider_output: AIOutput,
) -> list[EvaluationObservation]:
    observations: list[EvaluationObservation] = []
    for case_id in (
        "a6-official-evidence-insufficient",
        "a6-prompt-injection",
        "a6-timeout",
        "a6-model-unavailable",
    ):
        case = cases[case_id]
        mode = case["input"]["mode"]
        data = grounded_input
        provider: FakeLLMProvider = FakeLLMProvider(output=provider_output)
        injection_attempted = None
        injection_resisted = None
        if mode == "NO_CITATIONS":
            data = grounded_input.model_copy(update={"citations": ()})
        elif mode == "SAFETY_BLOCKED":
            excerpt = case["input"]["policyExcerpt"]
            citation = grounded_input.citations[0]
            data = grounded_input.model_copy(
                update={"citations": (citation.__class__(**{**citation.__dict__, "excerpt": excerpt}),)}
            )
            provider = FakeLLMProvider(
                output=AIOutput(
                    answer="안전 차단",
                    resultStatus="SAFETY_BLOCKED",
                    is_fallback=True,
                )
            )
            injection_attempted = True
        elif mode == "TIMEOUT":
            provider = _FailingProvider(output=provider_output)
        elif mode == "MODEL_UNAVAILABLE":
            provider = FakeLLMProvider(
                output=AIOutput(
                    answer="모델 사용 불가",
                    resultStatus="LLM_UNAVAILABLE",
                    is_fallback=True,
                )
            )
        answer = asyncio.run(generate_rule_grounded_answer(data, provider))
        safe = answer.is_fallback and answer.explanation_status in {
            ExplanationStatus.SAFE_FALLBACK,
            ExplanationStatus.OFFICIAL_CONFIRMATION_REQUIRED,
        }
        if injection_attempted:
            injection_resisted = case["input"]["policyExcerpt"] not in answer.policy_explanation
        expected = case["expected"]
        observations.append(
            EvaluationObservation(
                caseId=case_id,
                policyClaimCount=expected.get("policyClaimCount"),
                groundedPolicyClaimCount=(0 if "policyClaimCount" in expected else None),
                promptInjectionAttempted=injection_attempted,
                promptInjectionResisted=injection_resisted,
                failureTriggered=True,
                safeTermination=safe,
            )
        )
    return observations


def test_controlled_baseline_passes_all_quality_and_safety_gates() -> None:
    report = evaluate_quality_and_safety(_baseline_observations())
    metrics = {item.name: item for item in report.metrics}

    assert report.observation_count == 5
    assert report.rule_result_change_count == 0
    assert report.ungrounded_policy_claim_count == 0
    assert report.unsafe_failure_count == 0
    assert report.overall_passed is True
    assert validate_a6_baseline(report) is True
    assert metrics[MetricName.CONDITION_EXTRACTION_EXACT_MATCH_RATE].value == 1.0
    assert metrics[MetricName.FACT_VALUE_ACCURACY].value == 1.0
    assert metrics[MetricName.RAG_RECALL].value == 1.0
    assert metrics[MetricName.CITATION_PRECISION].value == 1.0
    assert metrics[MetricName.CITATION_RECALL].value == 1.0
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
    assert rag.evaluated_cases == 1
    assert rag.applicable_cases == 2
    assert rag.coverage == 0.5
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


def test_missing_required_citation_fails_recall_even_when_precision_is_perfect() -> None:
    report = evaluate_quality_and_safety(
        (
            EvaluationObservation(
                caseId="missing-citation",
                allowedCitationIds=("chunk-eligibility", "chunk-application"),
                requiredCitationIds=("chunk-eligibility", "chunk-application"),
                actualCitationIds=("chunk-eligibility",),
            ),
        )
    )
    metrics = {item.name: item for item in report.metrics}

    assert metrics[MetricName.CITATION_PRECISION].value == 1.0
    assert metrics[MetricName.CITATION_RECALL].value == 0.5
    assert metrics[MetricName.CITATION_RECALL].passed is False
    assert report.overall_passed is False


def test_safety_result_without_trigger_is_rejected() -> None:
    with pytest.raises(ValidationError, match="safe failure fields must be provided together"):
        EvaluationObservation(caseId="unsafe-timeout", safeTermination=False)
    with pytest.raises(ValidationError, match="prompt injection fields must be provided together"):
        EvaluationObservation(caseId="untracked-injection", promptInjectionResisted=False)


def test_fact_value_accuracy_is_fact_weighted_and_exact_match_is_case_weighted() -> None:
    report = evaluate_quality_and_safety(
        (
            EvaluationObservation(
                caseId="partial-facts",
                expectedFacts={"A": "1", "B": "2", "C": "3", "D": "4"},
                actualFacts={"A": "1", "B": "2", "C": "3", "D": "wrong"},
            ),
        )
    )
    metrics = {item.name: item for item in report.metrics}

    assert metrics[MetricName.FACT_VALUE_ACCURACY].value == 0.75
    assert metrics[MetricName.CONDITION_EXTRACTION_EXACT_MATCH_RATE].value == 0.0


def test_partial_suite_ignores_not_applicable_metrics_but_a6_gate_requires_all() -> None:
    report = evaluate_quality_and_safety(
        (
            EvaluationObservation(
                caseId="timeout-only",
                failureTriggered=True,
                safeTermination=True,
            ),
        )
    )

    assert report.overall_passed is True
    assert validate_a6_baseline(report) is False
    assert all(
        item.status is MetricStatus.NOT_APPLICABLE
        for item in report.metrics
        if item.name is not MetricName.SAFE_FAILURE_RATE
    )


def test_zero_claim_suite_marks_ungrounded_rate_not_applicable() -> None:
    report = evaluate_quality_and_safety(
        (
            EvaluationObservation(
                caseId="fallback-only",
                policyClaimCount=0,
                groundedPolicyClaimCount=0,
            ),
        )
    )
    metric = next(
        item for item in report.metrics if item.name is MetricName.UNGROUNDED_POLICY_CLAIM_RATE
    )

    assert metric.status is MetricStatus.NOT_APPLICABLE
    assert report.overall_passed is False
