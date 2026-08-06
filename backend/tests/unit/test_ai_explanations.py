import asyncio
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from app.llm import AIOutput, FakeLLMProvider, LLMRequest, LLMUnavailableError
from app.modules.ai.schemas import AIResponseStatus, CitationResponse
from app.modules.ai.service import (
    ExplanationContext,
    build_prompt,
    contradicts_rule_status,
    explain_with_ai,
    retrieved_context,
)


def policy(policy_id="policy_housing_001"):
    return SimpleNamespace(
        id=policy_id,
        title="Housing support",
        summary="Rent support",
        application_period="2026-01-01 to 2026-12-31",
        agency="Seoul Housing Office",
        region="Seoul",
        support_type="rent",
        official_source_url="https://example.go.kr/policy/1",
        source_label="OFFICIAL",
    )


def evaluation(status="LIKELY_INELIGIBLE", state="ACTIVE"):
    now = datetime(2026, 8, 6, 10, tzinfo=UTC)
    return SimpleNamespace(
        policy_id="policy_housing_001",
        eligibility_status=status,
        evaluation_state=state,
        evidence={
            "satisfied": [{"factKey": "region"}],
            "unsatisfied": [{"factKey": "income"}],
            "needsConfirmation": [{"factKey": "asset"}],
            "officialConfirmationRequired": [],
        },
        evaluated_at=now,
        updated_at=now,
    )


def citation():
    return CitationResponse(
        sourceId="chunk_doc_1",
        policyId="policy_housing_001",
        title="Official notice chunk",
        url="https://example.go.kr/policy/1",
        sourceLabel="OFFICIAL",
        evidenceId="chunk_1",
        excerpt="Official eligibility evidence.",
        sourceLocation="heading:eligibility",
        similarity=0.91,
    )


def json_answer(summary="The deterministic result is explained."):
    return (
        '{"summary":"'
        + summary
        + '","reasons":["The explanation follows stored rule evidence."],'
        + '"next_steps":["Review the official citation."],'
        + '"disclaimer":"Official confirmation may still be required."}'
    )

class FailingProvider:
    async def health(self):
        raise AssertionError("not used")

    async def check_health(self):
        return False

    async def generate(self, request: LLMRequest):
        _ = request
        raise LLMUnavailableError("ollama unavailable")


class SlowProvider:
    async def health(self):
        raise AssertionError("not used")

    async def check_health(self):
        return True

    async def generate(self, request: LLMRequest):
        _ = request
        await asyncio.sleep(10)
        raise AssertionError("timeout should happen first")


class AIExplanationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_llm_cannot_change_rule_status(self) -> None:
        provider = FakeLLMProvider(
            output=AIOutput(
                answer=json_answer("The stored rule result is likely ineligible."),
                resultStatus="ANSWERED",
                citations=[
                    {
                        "sourceId": "llm_doc",
                        "title": "LLM citation",
                        "url": "https://example.go.kr/other",
                        "policyVersionId": "policy_housing_001",
                        "evidenceId": "llm_chunk",
                    }
                ],
            )
        )

        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_INELIGIBLE"), (), (citation(),)),
            provider,
        )

        self.assertEqual(response.eligibility_status, "LIKELY_INELIGIBLE")
        self.assertEqual(response.ai_status, AIResponseStatus.GENERATED)
        self.assertEqual(response.citations[0].source_id, "chunk_doc_1")

    async def test_no_rag_evidence_uses_catalog_fallback_without_llm(self) -> None:
        provider = FakeLLMProvider()

        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_ELIGIBLE"), (), ()),
            provider,
        )

        self.assertEqual(response.eligibility_status, "LIKELY_ELIGIBLE")
        self.assertEqual(response.ai_status, AIResponseStatus.FALLBACK)
        self.assertEqual(response.citations[0].url, "https://example.go.kr/policy/1")
        self.assertIn("Housing support", response.answer)
        self.assertIn("Rule Engine 상태는 LIKELY_ELIGIBLE", response.answer)
        self.assertEqual(provider.requests, [])

    async def test_llm_failure_keeps_rule_decision_available_with_template_evidence(self) -> None:
        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_ELIGIBLE"), (), (citation(),)),
            FailingProvider(),
        )

        self.assertEqual(response.eligibility_status, "LIKELY_ELIGIBLE")
        self.assertEqual(response.ai_status, AIResponseStatus.FALLBACK)
        self.assertIn("Rule Engine 평가 상태는 LIKELY_ELIGIBLE", response.answer)
        self.assertIn("income", response.answer)
        self.assertIn("asset", response.answer)

    async def test_llm_timeout_uses_fallback_template(self) -> None:
        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("NEEDS_CONFIRMATION"), (), (citation(),)),
            SlowProvider(),
        )

        self.assertEqual(response.eligibility_status, "NEEDS_CONFIRMATION")
        self.assertEqual(response.ai_status, AIResponseStatus.FALLBACK)

    def test_prompt_marks_rule_result_read_only(self) -> None:
        prompt = build_prompt(ExplanationContext(policy(), evaluation(), (), (citation(),)), [citation()])

        self.assertIn("readOnlyRuleResult", prompt)
        self.assertIn("Do not change eligibilityStatus", prompt)
        self.assertIn("unmatchedConditions", prompt)

    async def test_contradictory_generated_answer_falls_back(self) -> None:
        provider = FakeLLMProvider(
            output=AIOutput(
                answer=json_answer("You are eligible and can apply."),
                resultStatus="ANSWERED",
                citations=[
                    {
                        "sourceId": "doc_1",
                        "title": "Official notice",
                        "url": "https://example.go.kr/policy/1",
                        "policyVersionId": "policy_housing_001",
                        "evidenceId": "chunk_1",
                    }
                ],
            )
        )

        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_INELIGIBLE"), (), (citation(),)),
            provider,
        )

        self.assertEqual(response.ai_status, AIResponseStatus.FALLBACK)
        self.assertIn("Rule Engine 평가 상태는 LIKELY_INELIGIBLE", response.answer)

    async def test_invalid_structured_answer_falls_back(self) -> None:
        provider = FakeLLMProvider(
            output=AIOutput(
                answer="plain text is not accepted",
                resultStatus="ANSWERED",
                citations=[
                    {
                        "sourceId": "doc_1",
                        "title": "Official notice",
                        "url": "https://example.go.kr/policy/1",
                        "policyVersionId": "policy_housing_001",
                        "evidenceId": "chunk_1",
                    }
                ],
            )
        )

        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_ELIGIBLE"), (), (citation(),)),
            provider,
        )

        self.assertEqual(response.ai_status, AIResponseStatus.FALLBACK)

    def test_retrieved_context_uses_delimiters(self) -> None:
        context = retrieved_context([citation()])

        self.assertIn("<retrieved_context>", context)
        self.assertIn("</retrieved_context>", context)
        self.assertIn("<citation", context)

    def test_contradiction_detector_blocks_positive_claims_for_ineligible_status(self) -> None:
        self.assertTrue(contradicts_rule_status("You can apply now.", "LIKELY_INELIGIBLE"))
        self.assertFalse(contradicts_rule_status("You can apply now.", "LIKELY_ELIGIBLE"))
