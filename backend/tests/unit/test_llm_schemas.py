import unittest

from pydantic import ValidationError

from app.llm import AIOutput, AIResultStatus


class AIOutputSchemaTests(unittest.TestCase):
    def test_ai_output_serializes_to_contract_shape(self) -> None:
        output = AIOutput(
            answer="소득 정보 확인이 필요합니다.",
            resultStatus=AIResultStatus.NEEDS_CONFIRMATION,
            matchedConditions=[{"conditionId": "region", "label": "거주 지역", "reason": "서울 거주"}],
            missingConditions=[{"conditionId": "income", "label": "가구 소득"}],
            citations=[
                {
                    "sourceId": "doc_1",
                    "title": "신혼부부 주거 지원 공고",
                    "url": "https://example.go.kr/policy/1",
                    "policyVersionId": "policy_version_1",
                    "excerpt": "소득 기준은 공고문을 확인하세요.",
                }
            ],
            nextQuestion={"questionId": "q_income", "prompt": "가구 소득 범위를 확인해 주세요.", "factKey": "income"},
        )

        payload = output.model_dump(by_alias=True)

        self.assertEqual(
            set(payload),
            {"answer", "resultStatus", "matchedConditions", "missingConditions", "citations", "nextQuestion"},
        )
        self.assertEqual(payload["resultStatus"], "NEEDS_CONFIRMATION")
        self.assertEqual(payload["matchedConditions"][0]["conditionId"], "region")
        self.assertEqual(payload["citations"][0]["policyVersionId"], "policy_version_1")
        self.assertEqual(payload["nextQuestion"]["factKey"], "income")

    def test_next_question_can_be_null(self) -> None:
        output = AIOutput(answer="근거가 부족해 답변할 수 없습니다.", resultStatus=AIResultStatus.INSUFFICIENT_EVIDENCE)

        self.assertIsNone(output.model_dump(by_alias=True)["nextQuestion"])

    def test_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(answer="x", resultStatus="ANSWERED", unexpected="value")

    def test_result_status_rejects_non_contract_values(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(answer="x", resultStatus="ELIGIBLE")
