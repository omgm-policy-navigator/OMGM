from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from app.catalog.models import Policy, PolicyDocument, PolicyEvaluation
from app.llm.providers import LLMError, LLMProvider, LLMRequest
from app.llm.schemas import AIResultStatus
from app.modules.ai.schemas import AIExplanationResponse, AIResponseStatus, CitationResponse
from app.modules.eligibility.rules import EligibilityStatus, EvaluationState

MAX_CITATIONS = 3
DEFAULT_ANSWER = (
    "Official evidence is required before an AI explanation can be trusted. "
    "Please check the official source."
)
LLM_SYSTEM_PROMPT = (
    "You explain policy evaluations in plain language. "
    "Do not change eligibilityStatus. Return the configured AIOutput JSON only."
)


@dataclass(frozen=True)
class ExplanationContext:
    policy: Policy | None
    evaluation: PolicyEvaluation | None
    documents: tuple[PolicyDocument, ...]
    retrieved_citations: tuple[CitationResponse, ...] = ()
    user_message: str | None = None


def citations_from_documents(documents: Iterable[PolicyDocument], policy_id: str) -> list[CitationResponse]:
    citations: list[CitationResponse] = []
    seen: set[str] = set()
    for document in documents:
        if document.id in seen:
            continue
        seen.add(document.id)
        citations.append(
            CitationResponse(
                sourceId=document.id,
                policyId=policy_id,
                title=document.title,
                url=document.url,
                sourceLabel=document.official_source,
                evidenceId=document.document_hash,
                excerpt=None,
            )
        )
        if len(citations) >= MAX_CITATIONS:
            break
    return citations


def rule_status(evaluation: PolicyEvaluation | None) -> tuple[str, str | None]:
    if evaluation is None:
        return EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED, None
    return evaluation.eligibility_status, evaluation.evaluation_state


def build_prompt(context: ExplanationContext, citations: list[CitationResponse]) -> str:
    policy = context.policy
    evaluation = context.evaluation
    payload = {
        "task": "Explain the rule evaluation using only the official citations.",
        "policy": None
        if policy is None
        else {
            "policyId": policy.id,
            "title": policy.title,
            "summary": policy.summary,
            "applicationPeriod": policy.application_period,
        },
        "ruleResult": None
        if evaluation is None
        else {
            "eligibilityStatus": evaluation.eligibility_status,
            "evaluationState": evaluation.evaluation_state,
            "evidence": evaluation.evidence,
        },
        "userMessage": context.user_message,
        "citations": [citation.model_dump(by_alias=True) for citation in citations],
        "constraints": [
            "Do not change eligibilityStatus.",
            "Do not cite uncited or unapproved documents.",
            "If evidence is insufficient, say official confirmation is required.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


async def explain_with_ai(context: ExplanationContext, provider: LLMProvider | None) -> AIExplanationResponse:
    policy_id = context.policy.id if context.policy is not None else None
    citations = (
        list(context.retrieved_citations)
        if context.retrieved_citations
        else citations_from_documents(context.documents, policy_id or "UNKNOWN")
        if policy_id is not None
        else []
    )
    eligibility_status, evaluation_state = rule_status(context.evaluation)

    if not citations:
        return AIExplanationResponse(
            policyId=policy_id,
            eligibilityStatus=EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED,
            evaluationState=evaluation_state,
            aiStatus=AIResponseStatus.OFFICIAL_CONFIRMATION_REQUIRED,
            answer=DEFAULT_ANSWER,
            citations=[],
        )

    if provider is None:
        return fallback_response(policy_id, eligibility_status, evaluation_state, citations)

    try:
        generated = await provider.generate(
            LLMRequest(prompt=build_prompt(context, citations), system=LLM_SYSTEM_PROMPT)
        )
    except (LLMError, RuntimeError, ValueError):
        return fallback_response(policy_id, eligibility_status, evaluation_state, citations)

    ai_status = AIResponseStatus.FALLBACK if generated.is_fallback else AIResponseStatus.GENERATED
    if generated.result_status in {AIResultStatus.LLM_UNAVAILABLE, AIResultStatus.SAFETY_BLOCKED}:
        ai_status = AIResponseStatus.FALLBACK
    return AIExplanationResponse(
        policyId=policy_id,
        eligibilityStatus=eligibility_status,
        evaluationState=evaluation_state,
        aiStatus=ai_status,
        answer=generated.answer,
        citations=citations,
    )


def fallback_response(
    policy_id: str | None,
    eligibility_status: str,
    evaluation_state: str | None,
    citations: list[CitationResponse],
) -> AIExplanationResponse:
    answer = (
        "AI explanation is temporarily unavailable. "
        "The rule evaluation result is still available with official citations."
    )
    if evaluation_state == EvaluationState.STALE:
        answer = (
            "AI explanation is temporarily unavailable. "
            "The saved rule evaluation is stale and should be recalculated."
        )
    return AIExplanationResponse(
        policyId=policy_id,
        eligibilityStatus=eligibility_status,
        evaluationState=evaluation_state,
        aiStatus=AIResponseStatus.FALLBACK,
        answer=answer,
        citations=citations,
    )
