from __future__ import annotations

import asyncio

from app.llm import AIOutput
from app.llm.fake import FakeLLMProvider
from app.modules.eligibility.rules import (
    ConditionEvidence,
    ConditionResult,
    EligibilityStatus,
    EvaluationResult,
)
from app.modules.explanations.generation import (
    ExplanationStatus,
    GraphNodeContext,
    GroundedAnswerInput,
    UserConditionContext,
    build_grounded_answer_request,
    generate_rule_grounded_answer,
)
from app.modules.rag.search import Citation


def evidence(rule_id: str, field: str, result: ConditionResult) -> ConditionEvidence:
    return ConditionEvidence(
        rule_id=rule_id,
        field=field,
        operator="EQ",
        expected="SEOUL",
        actual="SEOUL" if result is ConditionResult.MET else None,
        required=True,
        result=result,
        evidence=f"{field} 공식 조건",
    )


def citation(excerpt: str = "지원 한도는 100만원입니다.") -> Citation:
    return Citation(
        source_id="doc_1",
        evidence_id="chunk_1",
        policy_version_id="policy_1:2026-08-06",
        title="공식 공고",
        url="https://example.go.kr/policy/1",
        source_location="지원 내용 > 1문단",
        excerpt=excerpt,
        similarity=0.9,
    )


def request_data(
    status: EligibilityStatus = EligibilityStatus.LIKELY_ELIGIBLE,
    *,
    citations: tuple[Citation, ...] | None = None,
) -> GroundedAnswerInput:
    satisfied = (evidence("rule_region", "RESIDENCE_REGION", ConditionResult.MET),)
    missing: tuple[ConditionEvidence, ...] = ()
    if status is EligibilityStatus.NEEDS_CONFIRMATION:
        satisfied = ()
        missing = (evidence("rule_income", "HOUSEHOLD_INCOME_RANGE", ConditionResult.UNKNOWN),)
    return GroundedAnswerInput(
        user_question="이 정책을 신청할 수 있나요?",
        user_conditions=(UserConditionContext(key="RESIDENCE_REGION", value="SEOUL"),),
        evaluation=EvaluationResult(
            eligibility_status=status,
            satisfied=satisfied,
            needs_confirmation=missing,
        ),
        citations=(citation(),) if citations is None else citations,
        selected_graph_node=GraphNodeContext(
            node_id="policy_1", node_type="POLICY", label="신혼부부 지원"
        ),
    )


def answered_output(answer: str = "정책 설명: 거주 조건을 충족합니다.") -> AIOutput:
    return AIOutput(
        answer=answer,
        resultStatus="ANSWERED",
        matchedConditions=[
            {"conditionId": "rule_region", "label": "RESIDENCE_REGION", "reason": "공식 조건"}
        ],
        citations=[
            {
                "sourceId": "doc_1",
                "evidenceId": "chunk_1",
                "policyVersionId": "policy_1:2026-08-06",
                "title": "공식 공고",
                "url": "https://example.go.kr/policy/1",
                "excerpt": "지원 한도는 100만원입니다.",
            }
        ],
    )


def generate(data: GroundedAnswerInput, output: AIOutput) -> tuple[object, FakeLLMProvider]:
    provider = FakeLLMProvider(output=output)
    return asyncio.run(generate_rule_grounded_answer(data, provider)), provider


def test_grounded_answer_keeps_rule_result_and_input_evidence_authoritative() -> None:
    result, _ = generate(request_data(), answered_output())

    assert result.eligibility_status == "LIKELY_ELIGIBLE"
    assert result.explanation_status is ExplanationStatus.GROUNDED
    assert [item.condition_id for item in result.satisfied_conditions] == ["rule_region"]
    assert result.confirmation_conditions == []
    assert [item.evidence_id for item in result.official_sources] == ["chunk_1"]
    assert result.policy_explanation.startswith("정책 근거:")
    assert "지원 한도는 100만원입니다." in result.policy_explanation
    assert result.general_guidance.startswith("일반 안내:")


def test_opposite_rule_statement_is_replaced_with_safe_fallback() -> None:
    result, _ = generate(request_data(), answered_output("정책 설명: 이 정책은 신청할 수 없습니다."))

    assert result.eligibility_status == "LIKELY_ELIGIBLE"
    assert result.explanation_status is ExplanationStatus.SAFE_FALLBACK
    assert result.is_fallback is True
    assert "신청할 수 없습니다" not in result.policy_explanation


def test_uncited_policy_number_is_replaced_but_cited_number_is_allowed() -> None:
    rejected, _ = generate(request_data(), answered_output("정책 설명: 지원 한도는 200만원입니다."))
    accepted, _ = generate(request_data(), answered_output("정책 설명: 지원 한도는 100만원입니다."))

    assert rejected.explanation_status is ExplanationStatus.SAFE_FALLBACK
    assert accepted.explanation_status is ExplanationStatus.GROUNDED


def test_missing_evidence_requires_official_confirmation_without_calling_llm() -> None:
    provider = FakeLLMProvider(output=answered_output())
    result = asyncio.run(generate_rule_grounded_answer(request_data(citations=()), provider))

    assert result.explanation_status is ExplanationStatus.OFFICIAL_CONFIRMATION_REQUIRED
    assert result.official_sources == []
    assert "공식 문서 근거가 없어" in result.policy_explanation
    assert provider.requests == []


def test_llm_failure_returns_safe_fallback_without_changing_rule_result() -> None:
    class FailingProvider(FakeLLMProvider):
        async def generate(self, request: object) -> AIOutput:
            raise RuntimeError("provider unavailable")

    result = asyncio.run(generate_rule_grounded_answer(request_data(), FailingProvider()))

    assert result.eligibility_status == "LIKELY_ELIGIBLE"
    assert result.explanation_status is ExplanationStatus.SAFE_FALLBACK
    assert result.is_fallback is True


def test_missing_condition_and_status_must_match_rule_engine() -> None:
    data = request_data(EligibilityStatus.NEEDS_CONFIRMATION)
    valid = AIOutput(
        answer="정책 설명: 소득 조건을 추가로 확인해야 합니다.",
        resultStatus="NEEDS_CONFIRMATION",
        missingConditions=[
            {"conditionId": "rule_income", "label": "HOUSEHOLD_INCOME_RANGE", "reason": "추가 확인"}
        ],
        citations=answered_output().citations,
    )
    result, _ = generate(data, valid)

    assert result.eligibility_status == "NEEDS_CONFIRMATION"
    assert [item.condition_id for item in result.confirmation_conditions] == ["rule_income"]
    assert result.explanation_status is ExplanationStatus.GROUNDED


def test_invented_citation_is_rejected() -> None:
    output = answered_output().model_copy(deep=True)
    output.citations[0].evidence_id = "invented_chunk"
    result, _ = generate(request_data(), output)

    assert result.explanation_status is ExplanationStatus.SAFE_FALLBACK
    assert [item.evidence_id for item in result.official_sources] == ["chunk_1"]


def test_ineligible_answer_includes_unsatisfied_conditions() -> None:
    data = request_data().model_copy(
        update={
            "evaluation": EvaluationResult(
                eligibility_status=EligibilityStatus.LIKELY_INELIGIBLE,
                unsatisfied=(
                    evidence("rule_home", "HOME_OWNERSHIP", ConditionResult.UNMET),
                ),
            )
        }
    )
    output = answered_output().model_copy(
        update={"matched_conditions": []}
    )

    result, _ = generate(data, output)

    assert [item.condition_id for item in result.unsatisfied_conditions] == ["rule_home"]


def test_unsupported_qualitative_claim_is_not_exposed() -> None:
    output = answered_output(
        "이 정책은 온라인으로만 신청하며 다른 주거지원과 중복 신청은 불가능합니다."
    )

    result, _ = generate(
        request_data(citations=(citation("서울 거주 신혼부부가 신청 대상입니다."),)), output
    )

    assert result.explanation_status is ExplanationStatus.GROUNDED
    assert "온라인" not in result.policy_explanation
    assert "중복 신청" not in result.policy_explanation
    assert "서울 거주 신혼부부" in result.policy_explanation


def test_provider_fallback_is_replaced_with_server_fallback() -> None:
    output = answered_output().model_copy(update={"is_fallback": True})

    result, _ = generate(request_data(), output)

    assert result.explanation_status is ExplanationStatus.SAFE_FALLBACK
    assert result.is_fallback is True


def test_duplicate_rule_condition_ids_are_rejected() -> None:
    duplicate = evidence("rule_region", "RESIDENCE_REGION", ConditionResult.UNKNOWN)
    data = request_data().model_copy(
        update={
            "evaluation": EvaluationResult(
                eligibility_status=EligibilityStatus.NEEDS_CONFIRMATION,
                satisfied=(evidence("rule_region", "RESIDENCE_REGION", ConditionResult.MET),),
                needs_confirmation=(duplicate,),
            )
        }
    )

    try:
        generate(data, answered_output())
    except ValueError as error:
        assert str(error) == "rule result contains duplicate condition IDs"
    else:
        raise AssertionError("duplicate condition IDs must be rejected")


def test_prompt_contains_all_inputs_and_non_decision_constraints() -> None:
    request = build_grounded_answer_request(request_data())

    assert "userQuestion" in request.prompt
    assert "userConditions" in request.prompt
    assert "ruleResult" in request.prompt
    assert "retrievedChunks" in request.prompt
    assert "selectedGraphNode" in request.prompt
    assert "Never change or infer eligibility" in (request.system or "")
    assert "Do not state policy amounts" in (request.system or "")
