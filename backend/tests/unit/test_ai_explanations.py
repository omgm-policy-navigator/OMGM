import asyncio
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from app.llm import AIOutput, FakeLLMProvider, LLMRequest, LLMUnavailableError
from app.modules.ai.schemas import AIResponseStatus, CitationResponse
from app.modules.ai.service import ExplanationContext, build_prompt, explain_with_ai


def policy(policy_id="policy_housing_001"):
    return SimpleNamespace(
        id=policy_id,
        title="Housing support",
        summary="Rent support",
        application_period="2026-01-01 to 2026-12-31",
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
                answer="The user appears eligible, but this is only explanatory text.",
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

    async def test_no_rag_evidence_requires_confirmation_without_llm(self) -> None:
        provider = FakeLLMProvider()

        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_ELIGIBLE"), (), ()),
            provider,
        )

        self.assertEqual(response.eligibility_status, "OFFICIAL_CONFIRMATION_REQUIRED")
        self.assertEqual(response.ai_status, AIResponseStatus.OFFICIAL_CONFIRMATION_REQUIRED)
        self.assertEqual(response.citations, [])
        self.assertEqual(provider.requests, [])

    async def test_llm_failure_keeps_rule_decision_available_with_template_evidence(self) -> None:
        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_ELIGIBLE"), (), (citation(),)),
            FailingProvider(),
        )

        self.assertEqual(response.eligibility_status, "LIKELY_ELIGIBLE")
        self.assertEqual(response.ai_status, AIResponseStatus.FALLBACK)
        self.assertIn("Rule Engine status is LIKELY_ELIGIBLE", response.answer)
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
