from __future__ import annotations

import json
import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.llm.providers import LLMProvider, LLMRequest
from app.llm.schemas import AICitation, AIOutput, AIResultStatus
from app.modules.eligibility.rules import ConditionEvidence, EligibilityStatus, EvaluationResult
from app.modules.rag.search import Citation

_NUMBER_CLAIM = re.compile(r"(?<![A-Za-z0-9_])\d[\d,.]*(?:%|원|만원|억원|년|개월|일|세)?")
_OPPOSITE_PHRASES: dict[EligibilityStatus, tuple[str, ...]] = {
    EligibilityStatus.LIKELY_ELIGIBLE: ("신청할 수 없", "대상이 아닙", "부적격", "not eligible", "ineligible"),
    EligibilityStatus.LIKELY_INELIGIBLE: ("신청할 수 있습니다", "대상입니다", "eligible for"),
    EligibilityStatus.NEEDS_CONFIRMATION: (
        "신청할 수 있습니다",
        "신청할 수 없습니다",
        "대상입니다",
        "대상이 아닙니다",
    ),
    EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED: (
        "신청할 수 있습니다",
        "신청할 수 없습니다",
        "대상입니다",
        "대상이 아닙니다",
    ),
    EligibilityStatus.AVAILABLE_LATER: ("현재 신청할 수 있습니다", "신청할 수 없습니다", "대상이 아닙니다"),
}


class UserConditionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)


class GraphNodeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1, max_length=100)
    node_type: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)


class GroundedAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    user_question: str = Field(min_length=1, max_length=2000)
    user_conditions: tuple[UserConditionContext, ...] = Field(max_length=30)
    evaluation: EvaluationResult
    citations: tuple[Citation, ...] = Field(max_length=20)
    selected_graph_node: GraphNodeContext | None = None


class ConditionExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str = Field(alias="conditionId", min_length=1)
    label: str = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=500)


class ExplanationStatus(StrEnum):
    GROUNDED = "GROUNDED"
    OFFICIAL_CONFIRMATION_REQUIRED = "OFFICIAL_CONFIRMATION_REQUIRED"
    SAFE_FALLBACK = "SAFE_FALLBACK"


class RuleGroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    eligibility_status: str = Field(alias="eligibilityStatus")
    explanation_status: ExplanationStatus = Field(alias="explanationStatus")
    verdict_summary: str = Field(alias="verdictSummary", min_length=1, max_length=500)
    satisfied_conditions: list[ConditionExplanation] = Field(alias="satisfiedConditions")
    unsatisfied_conditions: list[ConditionExplanation] = Field(alias="unsatisfiedConditions")
    confirmation_conditions: list[ConditionExplanation] = Field(alias="confirmationConditions")
    application_timing: str = Field(alias="applicationTiming", min_length=1, max_length=500)
    official_sources: list[AICitation] = Field(alias="officialSources")
    next_action: str = Field(alias="nextAction", min_length=1, max_length=500)
    policy_explanation: str = Field(alias="policyExplanation", min_length=1, max_length=2000)
    general_guidance: str = Field(alias="generalGuidance", min_length=1, max_length=500)
    is_fallback: bool = Field(default=False, alias="isFallback")


def build_grounded_answer_request(data: GroundedAnswerInput) -> LLMRequest:
    payload = {
        "userQuestion": data.user_question,
        "userConditions": [{"key": item.key, "value": item.value} for item in data.user_conditions],
        "ruleResult": {
            "eligibilityStatus": data.evaluation.eligibility_status.value,
            "satisfied": [_condition_payload(item) for item in data.evaluation.satisfied],
            "unsatisfied": [_condition_payload(item) for item in data.evaluation.unsatisfied],
            "needsConfirmation": [
                _condition_payload(item) for item in data.evaluation.needs_confirmation
            ],
            "officialConfirmationRequired": [
                _condition_payload(item) for item in data.evaluation.official_confirmation_required
            ],
        },
        "retrievedChunks": [
            {
                "evidenceId": item.evidence_id,
                "title": item.title,
                "url": item.url,
                "sourceLocation": item.source_location,
                "excerpt": item.excerpt,
            }
            for item in data.citations
        ],
        "selectedGraphNode": (
            {
                "id": data.selected_graph_node.node_id,
                "type": data.selected_graph_node.node_type,
                "label": data.selected_graph_node.label,
            }
            if data.selected_graph_node
            else None
        ),
    }
    system = (
        "You explain a precomputed policy Rule Engine result. Never change or infer eligibility. "
        "Return the existing AIOutput JSON contract. Your answer is advisory draft text only; "
        "the server renders policy evidence directly from the cited excerpts. "
        "resultStatus and condition IDs must match the supplied ruleResult. "
        "Use only supplied evidence IDs and URLs. Do not state policy amounts, dates, percentages, ages, or durations "
        "unless the exact number occurs in a retrieved excerpt. "
        "Clearly label policy evidence separately from general guidance."
    )
    return LLMRequest(prompt=json.dumps(payload, ensure_ascii=False, separators=(",", ":")), system=system)


async def generate_rule_grounded_answer(data: GroundedAnswerInput, provider: LLMProvider) -> RuleGroundedAnswer:
    _validate_input(data)
    if not data.citations:
        return _fallback_answer(data, insufficient_evidence=True)
    try:
        output = await provider.generate(build_grounded_answer_request(data))
    except Exception:
        return _fallback_answer(data, insufficient_evidence=False)
    if not _is_safe_draft(data, output):
        return _fallback_answer(data, insufficient_evidence=False)
    if output.is_fallback:
        return _fallback_answer(data, insufficient_evidence=False)
    used_evidence_ids = {item.evidence_id for item in output.citations}
    return _assemble_answer(
        data,
        _policy_evidence_text(data.citations, used_evidence_ids),
        explanation_status=ExplanationStatus.GROUNDED,
        is_fallback=False,
        used_evidence_ids=used_evidence_ids,
    )


def _validate_input(data: GroundedAnswerInput) -> None:
    if not data.user_question.strip():
        raise ValueError("user_question must not be blank")
    condition_keys = [item.key for item in data.user_conditions]
    if len(condition_keys) != len(set(condition_keys)):
        raise ValueError("user conditions must not contain duplicate keys")
    evidence_ids = [item.evidence_id for item in data.citations]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("citations must not contain duplicate evidence IDs")
    groups = (
        data.evaluation.satisfied,
        data.evaluation.unsatisfied,
        data.evaluation.needs_confirmation,
        data.evaluation.official_confirmation_required,
    )
    condition_ids = [_condition_id(item) for group in groups for item in group]
    if len(condition_ids) > 100:
        raise ValueError("rule result must not contain more than 100 conditions")
    if len(condition_ids) != len(set(condition_ids)):
        raise ValueError("rule result contains duplicate condition IDs")


def _is_safe_draft(data: GroundedAnswerInput, output: AIOutput) -> bool:
    if output.is_fallback or not output.citations:
        return False
    if output.result_status != _expected_result_status(data.evaluation.eligibility_status):
        return False
    expected_satisfied = {_condition_id(item) for item in data.evaluation.satisfied}
    expected_missing = {
        _condition_id(item)
        for item in (*data.evaluation.needs_confirmation, *data.evaluation.official_confirmation_required)
    }
    if {item.condition_id for item in output.matched_conditions} != expected_satisfied:
        return False
    if {item.condition_id for item in output.missing_conditions} != expected_missing:
        return False
    citations_by_id = {item.evidence_id: item for item in data.citations}
    for citation in output.citations:
        source = citations_by_id.get(citation.evidence_id)
        if source is None or citation.url != source.url or citation.source_id != source.source_id:
            return False
    lowered = output.answer.casefold()
    if any(phrase.casefold() in lowered for phrase in _OPPOSITE_PHRASES[data.evaluation.eligibility_status]):
        return False
    allowed_numbers = {
        token for citation in data.citations for token in _NUMBER_CLAIM.findall(citation.excerpt)
    }
    return set(_NUMBER_CLAIM.findall(output.answer)) <= allowed_numbers


def _assemble_answer(
    data: GroundedAnswerInput,
    explanation: str,
    *,
    explanation_status: ExplanationStatus,
    is_fallback: bool,
    used_evidence_ids: set[str] | None = None,
) -> RuleGroundedAnswer:
    return RuleGroundedAnswer(
        eligibilityStatus=data.evaluation.eligibility_status.value,
        explanationStatus=explanation_status,
        verdictSummary=_verdict_summary(data.evaluation.eligibility_status),
        satisfiedConditions=[_condition_response(item) for item in data.evaluation.satisfied],
        unsatisfiedConditions=[_condition_response(item) for item in data.evaluation.unsatisfied],
        confirmationConditions=[
            _condition_response(item)
            for item in (*data.evaluation.needs_confirmation, *data.evaluation.official_confirmation_required)
        ],
        applicationTiming=_application_timing(data.evaluation.eligibility_status),
        officialSources=[
            _citation_response(item)
            for item in data.citations
            if used_evidence_ids is None or item.evidence_id in used_evidence_ids
        ],
        nextAction=_next_action(data),
        policyExplanation=explanation,
        generalGuidance="일반 안내: 최종 신청 전 공식 공고와 담당 기관에서 최신 기준을 확인하세요.",
        isFallback=is_fallback,
    )


def _fallback_answer(data: GroundedAnswerInput, *, insufficient_evidence: bool) -> RuleGroundedAnswer:
    if insufficient_evidence:
        explanation = "정책 설명: 인용할 공식 문서 근거가 없어 세부 정책 사실은 설명하지 않습니다."
    else:
        explanation = "정책 설명: 생성된 설명을 검증할 수 없어 구조화된 Rule 결과만 제공합니다."
    status = (
        ExplanationStatus.OFFICIAL_CONFIRMATION_REQUIRED
        if insufficient_evidence
        else ExplanationStatus.SAFE_FALLBACK
    )
    return _assemble_answer(data, explanation, explanation_status=status, is_fallback=True)


def _condition_id(item: ConditionEvidence) -> str:
    if not item.rule_id:
        raise ValueError("condition evidence requires rule_id")
    return item.rule_id


def _policy_evidence_text(citations: tuple[Citation, ...], used_ids: set[str]) -> str:
    excerpts = [item.excerpt.strip() for item in citations if item.evidence_id in used_ids]
    return "정책 근거:\n" + "\n".join(f"- {excerpt}" for excerpt in excerpts)


def _condition_payload(item: ConditionEvidence) -> dict[str, object]:
    return {"conditionId": _condition_id(item), "label": item.field, "result": item.result.value}


def _condition_response(item: ConditionEvidence) -> ConditionExplanation:
    return ConditionExplanation(conditionId=_condition_id(item), label=item.field, reason=item.evidence)


def _citation_response(item: Citation) -> AICitation:
    return AICitation(
        sourceId=item.source_id,
        evidenceId=item.evidence_id,
        policyVersionId=item.policy_version_id,
        title=item.title,
        url=item.url,
        excerpt=item.excerpt,
    )


def _expected_result_status(status: EligibilityStatus) -> AIResultStatus:
    if status in {EligibilityStatus.NEEDS_CONFIRMATION, EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED}:
        return AIResultStatus.NEEDS_CONFIRMATION
    return AIResultStatus.ANSWERED


def _verdict_summary(status: EligibilityStatus) -> str:
    return {
        EligibilityStatus.LIKELY_ELIGIBLE: "Rule Engine 결과상 현재 입력 조건은 충족 가능성이 높습니다.",
        EligibilityStatus.LIKELY_INELIGIBLE: "Rule Engine 결과상 충족하지 못한 필수 조건이 있습니다.",
        EligibilityStatus.NEEDS_CONFIRMATION: "Rule Engine 판정을 위해 추가 사용자 조건 확인이 필요합니다.",
        EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED: "구조화하기 어려운 조건은 공식 기관 확인이 필요합니다.",
        EligibilityStatus.AVAILABLE_LATER: "Rule Engine 결과상 현재는 신청 시점 전입니다.",
    }[status]


def _application_timing(status: EligibilityStatus) -> str:
    if status is EligibilityStatus.AVAILABLE_LATER:
        return "신청 시점: 공고에 명시된 접수 시작일 이후 다시 확인하세요."
    return "신청 시점: 인용된 공식 공고에서 현재 접수 기간을 확인하세요."


def _next_action(data: GroundedAnswerInput) -> str:
    if data.evaluation.needs_confirmation:
        return "다음 행동: 확인되지 않은 사용자 조건을 먼저 입력하세요."
    if data.evaluation.official_confirmation_required or not data.citations:
        return "다음 행동: 공식 공고 또는 담당 기관에서 확인하세요."
    if data.selected_graph_node is not None:
        return f"다음 행동: 선택한 {data.selected_graph_node.label} 노드의 공식 신청 경로를 확인하세요."
    return "다음 행동: 공식 출처에서 신청 절차와 제출 서류를 확인하세요."
