from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from app.catalog.models import Policy, PolicyDocument, PolicyEvaluation
from app.llm.providers import LLMError, LLMProvider, LLMRequest
from app.llm.schemas import AIResultStatus
from app.modules.ai.schemas import AIExplanationResponse, AIResponseStatus, CitationResponse
from app.modules.eligibility.rules import EligibilityStatus, EvaluationState

LLM_TIMEOUT_SECONDS = 3
DEFAULT_ANSWER = (
    "Official evidence is required before an AI explanation can be trusted. "
    "Please check the official source."
)
LLM_SYSTEM_PROMPT = (
    "Hard guardrail: evaluationState, eligibilityStatus, satisfied conditions, unsatisfied conditions, "
    "and missing conditions are read-only context. Never change, override, soften, or contradict them. "
    "Your only role is to explain the deterministic Rule Engine result and summarize official next steps "
    "using the provided citations. Return the configured AIOutput JSON only."
)


@dataclass(frozen=True)
class ExplanationContext:
    policy: Policy | None
    evaluation: PolicyEvaluation | None
    documents: tuple[PolicyDocument, ...]
    retrieved_citations: tuple[CitationResponse, ...] = ()
    user_message: str | None = None


def rule_status(evaluation: PolicyEvaluation | None) -> tuple[str, str | None]:
    if evaluation is None:
        return EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED, None
    return evaluation.eligibility_status, evaluation.evaluation_state


def build_prompt(context: ExplanationContext, citations: list[CitationResponse]) -> str:
    policy = context.policy
    evaluation = context.evaluation
    evidence = evaluation.evidence if evaluation is not None else {}
    payload = {
        "task": "Explain the deterministic rule evaluation using only read-only rule context and citations.",
        "role": "Explain eligibility result and official next steps. Do not decide eligibility.",
        "policy": None
        if policy is None
        else {
            "policyId": policy.id,
            "title": policy.title,
            "summary": policy.summary,
            "applicationPeriod": policy.application_period,
        },
        "readOnlyRuleResult": None
        if evaluation is None
        else {
            "eligibilityStatus": evaluation.eligibility_status,
            "evaluationState": evaluation.evaluation_state,
            "matchedConditions": evidence.get("satisfied", []),
            "unmatchedConditions": evidence.get("unsatisfied", []),
            "missingConditions": evidence.get("needsConfirmation", []),
            "officialConfirmationRequired": evidence.get("officialConfirmationRequired", []),
        },
        "citations": [citation.model_dump(by_alias=True) for citation in citations],
        "constraints": [
            "Do not change eligibilityStatus or evaluationState.",
            "Do not say the user can apply when eligibilityStatus is not LIKELY_ELIGIBLE.",
            "Do not cite uncited or unapproved documents.",
            "Do not use personal facts beyond the read-only rule evidence summary.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


async def explain_with_ai(context: ExplanationContext, provider: LLMProvider | None) -> AIExplanationResponse:
    policy_id = context.policy.id if context.policy is not None else None
    citations = list(context.retrieved_citations)
    eligibility_status, evaluation_state = rule_status(context.evaluation)

    if not citations:
        return AIExplanationResponse(
            policyId=policy_id,
            eligibilityStatus=EligibilityStatus.OFFICIAL_CONFIRMATION_REQUIRED,
            evaluationState=evaluation_state,
            aiStatus=AIResponseStatus.OFFICIAL_CONFIRMATION_REQUIRED,
            answer=official_confirmation_answer(context),
            citations=[],
        )

    if provider is None:
        return fallback_response(policy_id, eligibility_status, evaluation_state, citations, context.evaluation)

    try:
        generated = await asyncio.wait_for(
            provider.generate(LLMRequest(prompt=build_prompt(context, citations), system=LLM_SYSTEM_PROMPT)),
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except (TimeoutError, LLMError, RuntimeError, ValueError):
        return fallback_response(policy_id, eligibility_status, evaluation_state, citations, context.evaluation)

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


def official_confirmation_answer(context: ExplanationContext) -> str:
    if context.policy is None:
        return DEFAULT_ANSWER
    return (
        "No approved RAG evidence was found for this policy explanation. "
        "The policy result requires official confirmation before AI explanation is shown."
    )


def fallback_response(
    policy_id: str | None,
    eligibility_status: str,
    evaluation_state: str | None,
    citations: list[CitationResponse],
    evaluation: PolicyEvaluation | None,
) -> AIExplanationResponse:
    return AIExplanationResponse(
        policyId=policy_id,
        eligibilityStatus=eligibility_status,
        evaluationState=evaluation_state,
        aiStatus=AIResponseStatus.FALLBACK,
        answer=template_answer(eligibility_status, evaluation_state, evaluation),
        citations=citations,
    )


def template_answer(
    eligibility_status: str,
    evaluation_state: str | None,
    evaluation: PolicyEvaluation | None,
) -> str:
    if evaluation_state == EvaluationState.STALE:
        return "The saved rule evaluation is stale. Please recalculate the policy evaluation before relying on it."
    evidence = evaluation.evidence if evaluation is not None else {}
    unmatched = _fact_keys(evidence.get("unsatisfied", []))
    missing = _fact_keys(evidence.get("needsConfirmation", []))
    parts = [f"Rule Engine status is {eligibility_status}."]
    if unmatched:
        parts.append("Unmatched required conditions: " + ", ".join(unmatched) + ".")
    if missing:
        parts.append("Missing confirmation conditions: " + ", ".join(missing) + ".")
    parts.append("AI explanation is temporarily unavailable, so this template uses the stored JSON evidence.")
    return " ".join(parts)


def _fact_keys(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    keys = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("factKey"), str):
            keys.append(item["factKey"])
    return keys[:5]
