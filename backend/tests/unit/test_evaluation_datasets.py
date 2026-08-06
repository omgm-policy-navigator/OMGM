from __future__ import annotations

import asyncio
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.llm.fake import FakeLLMProvider
from app.llm.schemas import AICitation, AIOutput
from app.modules.eligibility.rules import (
    Condition,
    ConditionEvidence,
    ConditionResult,
    EligibilityStatus,
    EvaluationResult,
    PolicyWindow,
    RuleEvaluationMode,
    evaluate_conditions,
)
from app.modules.explanations.generation import (
    ExplanationStatus,
    GroundedAnswerInput,
    UserConditionContext,
    generate_rule_grounded_answer,
)
from app.modules.rag.search import Citation, SearchHit, search_policy_evidence
from app.modules.user_facts.extraction import (
    AllowedFactKey,
    ConditionExtractionError,
    ExistingUserFact,
    build_condition_extraction_request,
    parse_condition_extraction,
    review_condition_extraction,
)

DATASET_DIR = Path(__file__).parents[1] / "fixtures" / "evaluation"
DATASET_FILES = {
    "rule-engine-cases.json",
    "rag-retrieval-cases.json",
    "fact-extraction-cases.json",
    "e2e-scenarios.json",
    "security-cases.json",
}
REQUIRED_SCENARIO_TAGS = {
    "all_conditions_met",
    "income_unknown",
    "marriage_status_conflict",
    "application_ended",
    "available_later",
    "official_evidence_insufficient",
    "policy_source_changed",
}
ELIGIBILITY_STATUSES = {item.value for item in EligibilityStatus}
EVALUATION_STATES = {"ACTIVE", "STALE", "CONFLICTED", "NOT_EVALUATED"}


def _load(name: str) -> dict[str, Any]:
    return json.loads((DATASET_DIR / name).read_text(encoding="utf-8"))


def _schema_major(version: str) -> int:
    major, separator, minor = version.partition(".")
    assert separator and major.isdigit() and minor.isdigit(), f"invalid schemaVersion: {version}"
    return int(major)


def test_d5_dataset_manifest_and_common_contract() -> None:
    assert {path.name for path in DATASET_DIR.glob("*.json")} == DATASET_FILES

    case_ids: list[str] = []
    tags: set[str] = set()
    for name in sorted(DATASET_FILES):
        document = _load(name)
        assert _schema_major(document["schemaVersion"]) == 1
        assert isinstance(document["dataset"], str) and document["dataset"]
        assert isinstance(document["cases"], list) and document["cases"]
        for case in document["cases"]:
            assert set(case) == {"id", "title", "tags", "input", "expected"}
            assert case["id"] and case["title"]
            assert isinstance(case["tags"], list) and case["tags"]
            assert isinstance(case["input"], dict)
            assert isinstance(case["expected"], dict) and case["expected"]
            case_ids.append(case["id"])
            tags.update(case["tags"])

            status = case["expected"].get("eligibilityStatus")
            state = case["expected"].get("evaluationState")
            assert status is None or status in ELIGIBILITY_STATUSES
            assert state is None or state in EVALUATION_STATES

    assert len(case_ids) == len(set(case_ids))
    assert REQUIRED_SCENARIO_TAGS <= tags


def test_rule_engine_cases_match_current_engine_contract() -> None:
    for case in _load("rule-engine-cases.json")["cases"]:
        payload = case["input"]
        conditions = [
            Condition(
                rule_id=item["ruleId"],
                field=item["field"],
                operator=item["operator"],
                expected=item["expected"],
                required=item["required"],
                evaluation_mode=RuleEvaluationMode(
                    item.get("evaluationMode", RuleEvaluationMode.DETERMINISTIC)
                ),
            )
            for item in payload["conditions"]
        ]
        window_data = payload.get("policyWindow")
        window = None
        if window_data:
            window = PolicyWindow(
                starts_at=date.fromisoformat(window_data["startsAt"]),
                ends_at=date.fromisoformat(window_data["endsAt"]),
            )
        result = evaluate_conditions(
            conditions,
            payload["facts"],
            policy_window=window,
            evaluation_time=date.fromisoformat(payload["evaluationDate"]),
        )
        expected = case["expected"]
        assert result.eligibility_status.value == expected["eligibilityStatus"], case["id"]
        assert result.evaluation_state.value == expected["evaluationState"], case["id"]
        if "recommendationScore" in expected:
            assert result.recommendation_score == expected["recommendationScore"], case["id"]
        if "satisfiedRuleIds" in expected:
            assert [item.rule_id for item in result.satisfied] == expected["satisfiedRuleIds"], case["id"]
        if "unsatisfiedRuleIds" in expected:
            assert [item.rule_id for item in result.unsatisfied] == expected["unsatisfiedRuleIds"], case["id"]
        if "needsConfirmationRuleIds" in expected:
            assert [item.rule_id for item in result.needs_confirmation] == expected[
                "needsConfirmationRuleIds"
            ], case["id"]
        if "officialConfirmationRuleIds" in expected:
            assert [item.rule_id for item in result.official_confirmation_required] == expected[
                "officialConfirmationRuleIds"
            ], case["id"]


def test_fact_extraction_cases_use_allowlist_and_expected_review_state() -> None:
    allowed_keys = {item.value for item in AllowedFactKey}
    for case in _load("fact-extraction-cases.json")["cases"]:
        payload = case["input"]
        raw_output = json.dumps({"candidates": payload["modelCandidates"]}, ensure_ascii=False)
        if "parseError" in case["expected"]:
            with pytest.raises(ConditionExtractionError):
                parse_condition_extraction(raw_output)
            continue

        output = parse_condition_extraction(raw_output)
        existing = [
            ExistingUserFact(
                fact_key=item["factKey"], value=item["value"], confirmed=item["confirmed"]
            )
            for item in payload["existingFacts"]
        ]
        original_existing = [item.model_copy(deep=True) for item in existing]
        reviewed = review_condition_extraction(output, payload["userText"], existing)
        assert {item.fact_key.value for item in reviewed.candidates} <= allowed_keys
        assert [item.fact_key.value for item in reviewed.candidates] == case["expected"][
            "acceptedFactKeys"
        ]
        assert reviewed.needs_confirmation is case["expected"]["needsConfirmation"]
        if "requiresNormalization" in case["expected"]:
            assert all(
                item.requires_normalization is case["expected"]["requiresNormalization"]
                for item in reviewed.candidates
            )
        if case["expected"].get("mustNotPersistAsConfirmed"):
            assert all(item.requires_confirmation for item in reviewed.candidates)
        if case["expected"].get("mustNotCoerceTo"):
            assert all(
                item.raw_value not in case["expected"]["mustNotCoerceTo"]
                for item in reviewed.candidates
            )
        conflicts = [
            {
                "factKey": item.fact_key.value,
                "previousValue": item.previous_value,
                "candidateValue": item.candidate_value,
                "resolutionRequired": item.resolution_required,
            }
            for item in reviewed.conflicts
        ]
        assert conflicts == case["expected"]["conflicts"]
        if case["expected"].get("mustNotOverwriteConfirmedFact"):
            assert existing == original_existing


class _D5EmbeddingProvider:
    model = "qwen3-embedding:0.6b"

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((0.1,) for _ in texts)


class _D5RagRepository:
    def __init__(self, candidates: list[dict[str, Any]]) -> None:
        self.candidates = candidates

    async def search(
        self,
        *,
        policy_id: str,
        embedding: tuple[float, ...],
        model: str,
        top_k: int,
        minimum_similarity: float,
    ) -> tuple[SearchHit, ...]:
        del embedding, model
        eligible = [
            item
            for item in self.candidates
            if item["policyId"] == policy_id
            and item["documentStatus"] == "APPROVED"
            and item["trustLevel"] == "OFFICIAL"
            and item["policyStatus"] == "ACTIVE"
            and item["similarity"] >= minimum_similarity
        ]
        return tuple(
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
            for item in eligible[:top_k]
        )


def test_rag_cases_execute_search_and_exact_citation_mapping() -> None:
    for case in _load("rag-retrieval-cases.json")["cases"]:
        payload = case["input"]
        result = asyncio.run(
            search_policy_evidence(
                policy_id=payload["policyId"],
                question=payload["question"],
                provider=_D5EmbeddingProvider(),
                repository=_D5RagRepository(payload["candidates"]),
                top_k=payload["topK"],
                minimum_similarity=payload["minimumSimilarity"],
            )
        )
        citations = [
            {
                "evidenceId": item.evidence_id,
                "policyVersionId": item.policy_version_id,
                "url": item.url,
                "sourceLocation": item.source_location,
            }
            for item in result.citations
        ]
        assert citations == case["expected"]["citations"], case["id"]
        assert result.insufficient_evidence is case["expected"]["insufficientEvidence"], case["id"]


def test_e2e_cases_reference_executable_component_cases() -> None:
    rule_cases = {item["id"]: item for item in _load("rule-engine-cases.json")["cases"]}
    fact_cases = {item["id"]: item for item in _load("fact-extraction-cases.json")["cases"]}
    rag_cases = {item["id"]: item for item in _load("rag-retrieval-cases.json")["cases"]}
    for case in _load("e2e-scenarios.json")["cases"]:
        payload = case["input"]
        if "ruleCaseId" in payload:
            referenced = rule_cases[payload["ruleCaseId"]]
            assert referenced["expected"]["eligibilityStatus"] == case["expected"]["eligibilityStatus"]
        if "factCaseId" in payload:
            assert payload["factCaseId"] in fact_cases
        if "retrievalCaseId" in payload:
            referenced = rag_cases[payload["retrievalCaseId"]]
            assert referenced["expected"]["insufficientEvidence"] is case["expected"].get(
                "rag", {"insufficientEvidence": referenced["expected"]["insufficientEvidence"]}
            )["insufficientEvidence"]


def test_security_cases_execute_public_boundaries() -> None:
    cases = {item["id"]: item for item in _load("security-cases.json")["cases"]}
    private_url = cases["security-private-citation-url"]
    with pytest.raises(ValidationError):
        AICitation(
            sourceId="document-1",
            evidenceId="chunk-1",
            policyVersionId="version-1",
            title="공식 문서",
            url=private_url["input"]["citationUrl"],
        )

    oversized = cases["security-oversized-user-input"]
    with pytest.raises(ValueError, match="at most 4000"):
        build_condition_extraction_request("가" * oversized["input"]["length"])

    allowed_citation = Citation(
        source_id="document-1",
        evidence_id="chunk-approved",
        policy_version_id="version-1",
        title="공식 문서",
        url="https://example.go.kr/policy/1",
        source_location="신청자격 > 1문단",
        excerpt="서울 거주 조건입니다.",
        similarity=0.9,
    )
    grounded_input = GroundedAnswerInput(
        user_question="신청할 수 있나요?",
        user_conditions=(UserConditionContext(key="RESIDENCE_REGION", value="SEOUL"),),
        evaluation=EvaluationResult(
            eligibility_status=EligibilityStatus.LIKELY_ELIGIBLE,
            satisfied=(
                ConditionEvidence(
                    rule_id="rule-region",
                    field="RESIDENCE_REGION",
                    operator="EQ",
                    expected="SEOUL",
                    actual="SEOUL",
                    required=True,
                    result=ConditionResult.MET,
                ),
            ),
        ),
        citations=(allowed_citation,),
    )

    invented = cases["security-invented-citation"]
    invented_output = AIOutput(
        answer="공식 근거 설명",
        resultStatus="ANSWERED",
        matchedConditions=[{"conditionId": "rule-region", "label": "RESIDENCE_REGION"}],
        citations=[
            {
                "sourceId": "document-2",
                "evidenceId": invented["input"]["modelEvidenceIds"][0],
                "policyVersionId": "version-1",
                "title": "조작 문서",
                "url": "https://example.go.kr/invented",
            }
        ],
    )
    invented_result = asyncio.run(
        generate_rule_grounded_answer(grounded_input, FakeLLMProvider(output=invented_output))
    )
    assert invented_result.explanation_status.value == invented["expected"]["explanationStatus"]
    assert [item.evidence_id for item in invented_result.official_sources] == invented["expected"][
        "officialEvidenceIds"
    ]
    assert invented["input"]["modelEvidenceIds"][0] not in {
        item.evidence_id for item in invented_result.official_sources
    }

    injection = cases["security-policy-prompt-injection"]
    blocked_result = asyncio.run(
        generate_rule_grounded_answer(
            grounded_input.model_copy(
                update={
                    "citations": (
                        Citation(
                            **{
                                **allowed_citation.__dict__,
                                "excerpt": injection["input"]["policyExcerpt"],
                            }
                        ),
                    )
                }
            ),
            FakeLLMProvider(
                output=AIOutput(answer="요청을 차단했습니다.", resultStatus="SAFETY_BLOCKED", is_fallback=True)
            ),
        )
    )
    assert blocked_result.explanation_status is ExplanationStatus.SAFE_FALLBACK
    assert injection["input"]["policyExcerpt"] not in blocked_result.policy_explanation


def test_all_evaluation_fixtures_exclude_sensitive_values_and_secret_keys() -> None:
    documents = [_load(name) for name in DATASET_FILES]
    serialized = json.dumps(documents, ensure_ascii=False)
    forbidden_patterns = (
        re.compile(r"\b01[016789][-. ]?\d{3,4}[-. ]?\d{4}\b"),
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        re.compile(r"\b\d{6}[- ]?[1-4]\d{6}\b"),
    )
    assert all(pattern.search(serialized) is None for pattern in forbidden_patterns)

    forbidden_keys = {"password", "accesstoken", "refreshtoken", "secretkey", "authorization"}

    def keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return {str(key).casefold() for key in value} | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert not (keys(documents) & forbidden_keys)
