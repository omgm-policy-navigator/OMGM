import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from app.llm import AIOutput, FakeLLMProvider, LLMRequest, LLMUnavailableError
from app.modules.ai.schemas import AIResponseStatus
from app.modules.ai.service import ExplanationContext, explain_with_ai


def policy(policy_id="policy_housing_001"):
    return SimpleNamespace(
        id=policy_id,
        title="Housing support",
        summary="Rent support",
        application_period="2026-01-01 to 2026-12-31",
    )


def document(policy_id="policy_housing_001"):
    return SimpleNamespace(
        id="doc_1",
        policy_id=policy_id,
        title="Official notice",
        url="https://example.go.kr/policy/1",
        official_source="Example Office",
        document_hash="hash_1",
    )


def evaluation(status="LIKELY_INELIGIBLE", state="ACTIVE"):
    now = datetime(2026, 8, 6, 10, tzinfo=UTC)
    return SimpleNamespace(
        policy_id="policy_housing_001",
        eligibility_status=status,
        evaluation_state=state,
        evidence={"satisfied": [], "unsatisfied": []},
        evaluated_at=now,
        updated_at=now,
    )


class FailingProvider:
    async def health(self):
        raise AssertionError("not used")

    async def check_health(self):
        return False

    async def generate(self, request: LLMRequest):
        _ = request
        raise LLMUnavailableError("ollama unavailable")


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
            ExplanationContext(policy(), evaluation("LIKELY_INELIGIBLE"), (document(),)),
            provider,
        )

        self.assertEqual(response.eligibility_status, "LIKELY_INELIGIBLE")
        self.assertEqual(response.ai_status, AIResponseStatus.GENERATED)
        self.assertEqual(response.citations[0].source_id, "doc_1")

    async def test_no_official_evidence_requires_confirmation(self) -> None:
        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_ELIGIBLE"), ()),
            FakeLLMProvider(),
        )

        self.assertEqual(response.eligibility_status, "OFFICIAL_CONFIRMATION_REQUIRED")
        self.assertEqual(response.ai_status, AIResponseStatus.OFFICIAL_CONFIRMATION_REQUIRED)
        self.assertEqual(response.citations, [])

    async def test_llm_failure_keeps_rule_decision_available(self) -> None:
        response = await explain_with_ai(
            ExplanationContext(policy(), evaluation("LIKELY_ELIGIBLE"), (document(),)),
            FailingProvider(),
        )

        self.assertEqual(response.eligibility_status, "LIKELY_ELIGIBLE")
        self.assertEqual(response.ai_status, AIResponseStatus.FALLBACK)
        self.assertEqual(response.citations[0].source_id, "doc_1")
