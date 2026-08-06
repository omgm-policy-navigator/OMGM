import unittest

from pydantic import ValidationError

from app.llm import AIOutput, AIResultStatus


class AIOutputSchemaTests(unittest.TestCase):
    def test_answered_output_serializes_to_contract_shape(self) -> None:
        output = AIOutput(
            answer="공고문 기준으로 거주 지역 조건은 충족합니다.",
            resultStatus=AIResultStatus.ANSWERED,
            matchedConditions=[{"conditionId": "region", "label": "거주 지역", "reason": "서울 거주"}],
            citations=[
                {
                    "sourceId": "doc_1",
                    "title": "신혼부부 주거 지원 공고",
                    "url": "https://example.go.kr/policy/1",
                    "policyVersionId": "policy_version_1",
                    "evidenceId": "chunk_1",
                    "excerpt": "소득 기준은 공고문을 확인하세요.",
                }
            ],
        )

        payload = output.model_dump(by_alias=True)

        self.assertEqual(
            set(payload),
            {
                "answer",
                "resultStatus",
                "is_fallback",
                "matchedConditions",
                "missingConditions",
                "citations",
                "nextQuestion",
            },
        )
        self.assertEqual(payload["resultStatus"], "ANSWERED")
        self.assertEqual(payload["is_fallback"], False)
        self.assertEqual(payload["matchedConditions"][0]["conditionId"], "region")
        self.assertEqual(payload["citations"][0]["policyVersionId"], "policy_version_1")
        self.assertEqual(payload["citations"][0]["evidenceId"], "chunk_1")
        self.assertEqual(payload["nextQuestion"], None)

    def test_needs_confirmation_requires_missing_conditions(self) -> None:
        output = AIOutput(
            answer="소득 정보 확인이 필요합니다.",
            resultStatus=AIResultStatus.NEEDS_CONFIRMATION,
            missingConditions=[{"conditionId": "income", "label": "가구 소득"}],
            nextQuestion={"questionId": "q_income", "prompt": "가구 소득 범위를 확인해 주세요.", "factKey": "income"},
        )

        self.assertEqual(output.result_status, AIResultStatus.NEEDS_CONFIRMATION)

    def test_next_question_can_be_null(self) -> None:
        output = AIOutput(answer="근거가 부족해 답변할 수 없습니다.", resultStatus=AIResultStatus.INSUFFICIENT_EVIDENCE)

        self.assertIsNone(output.model_dump(by_alias=True)["nextQuestion"])

    def test_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(answer="AI 설명을 생성할 수 없습니다.", resultStatus="LLM_UNAVAILABLE", unexpected="value")

    def test_result_status_rejects_non_contract_values(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(answer="x", resultStatus="ELIGIBLE")

    def test_answered_requires_citation(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(answer="이 정책의 대상입니다.", resultStatus="ANSWERED")

    def test_answered_rejects_missing_conditions_and_next_question(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(
                answer="확인이 필요합니다.",
                resultStatus="ANSWERED",
                missingConditions=[{"conditionId": "income", "label": "가구 소득"}],
                citations=[
                    {
                        "sourceId": "doc_1",
                        "title": "공고",
                        "url": "https://example.go.kr/policy/1",
                        "policyVersionId": "policy_version_1",
                        "evidenceId": "chunk_1",
                    }
                ],
                nextQuestion={"questionId": "q_income", "prompt": "소득을 확인해 주세요.", "factKey": "income"},
            )

    def test_needs_confirmation_requires_missing_condition_reference(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(answer="확인이 필요합니다.", resultStatus="NEEDS_CONFIRMATION")

    def test_insufficient_evidence_rejects_citations(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(
                answer="근거가 부족합니다.",
                resultStatus="INSUFFICIENT_EVIDENCE",
                citations=[
                    {
                        "sourceId": "doc_1",
                        "title": "공고",
                        "url": "https://example.go.kr/policy/1",
                        "policyVersionId": "policy_version_1",
                        "evidenceId": "chunk_1",
                    }
                ],
            )

    def test_llm_unavailable_rejects_derived_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(
                answer="AI 설명을 생성할 수 없습니다.",
                resultStatus="LLM_UNAVAILABLE",
                citations=[
                    {
                        "sourceId": "doc_1",
                        "title": "공고",
                        "url": "https://example.go.kr/policy/1",
                        "policyVersionId": "policy_version_1",
                        "evidenceId": "chunk_1",
                    }
                ],
            )

    def test_safety_blocked_rejects_condition_references(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(
                answer="요청을 처리할 수 없습니다.",
                resultStatus="SAFETY_BLOCKED",
                matchedConditions=[{"conditionId": "region", "label": "거주 지역"}],
            )

    def test_citation_url_must_be_public_http_url(self) -> None:
        blocked_urls = [
            "javascript:alert(1)",
            "file:///tmp/policy.pdf",
            "http://localhost/policy/1",
            "http://service.localhost/policy/1",
            "http://127.0.0.1/policy/1",
            "http://10.0.0.1/internal",
            "http://192.168.0.10/admin",
            "http://172.16.0.5/document",
            "http://169.254.169.254/latest/meta-data",
            "http://[fc00::1]/internal",
            "http://[::1]/internal",
        ]

        for url in blocked_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    AIOutput(
                        answer="공고를 확인했습니다.",
                        resultStatus="ANSWERED",
                        citations=[
                            {
                                "sourceId": "doc_1",
                                "title": "공고",
                                "url": url,
                                "policyVersionId": "policy_version_1",
                                "evidenceId": "chunk_1",
                            }
                        ],
                    )

    def test_citation_url_allows_public_http_domain(self) -> None:
        output = AIOutput(
            answer="공고를 확인했습니다.",
            resultStatus="ANSWERED",
            citations=[
                {
                    "sourceId": "doc_1",
                    "title": "공고",
                    "url": "https://example.go.kr/policy/1",
                    "policyVersionId": "policy_version_1",
                    "evidenceId": "chunk_1",
                }
            ],
        )

        self.assertEqual(output.citations[0].url, "https://example.go.kr/policy/1")

    def test_empty_identifier_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(
                answer="공고를 확인했습니다.",
                resultStatus="ANSWERED",
                citations=[
                    {
                        "sourceId": "",
                        "title": "공고",
                        "url": "https://example.go.kr/policy/1",
                        "policyVersionId": "policy_version_1",
                        "evidenceId": "chunk_1",
                    }
                ],
            )

    def test_duplicate_citation_evidence_id_is_rejected(self) -> None:
        citation = {
            "sourceId": "doc_1",
            "title": "공고",
            "url": "https://example.go.kr/policy/1",
            "policyVersionId": "policy_version_1",
            "evidenceId": "chunk_1",
        }

        with self.assertRaises(ValidationError):
            AIOutput(answer="공고를 확인했습니다.", resultStatus="ANSWERED", citations=[citation, citation])

    def test_condition_cannot_be_both_matched_and_missing(self) -> None:
        with self.assertRaises(ValidationError):
            AIOutput(
                answer="확인이 필요합니다.",
                resultStatus="NEEDS_CONFIRMATION",
                matchedConditions=[{"conditionId": "income", "label": "소득"}],
                missingConditions=[{"conditionId": "income", "label": "소득"}],
            )
