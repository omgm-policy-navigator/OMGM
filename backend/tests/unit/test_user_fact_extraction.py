import json
import unittest

from app.modules.user_facts import (
    AllowedFactKey,
    ConditionExtractionError,
    ExistingUserFact,
    build_condition_extraction_request,
    parse_condition_extraction,
    review_condition_extraction,
)


def model_output(**overrides: object) -> str:
    candidate: dict[str, object] = {
        "factKey": "RESIDENCE_REGION",
        "value": "SEOUL",
        "confidence": 0.95,
        "isAmbiguous": False,
        "evidence": "서울에 살고 있어요",
    }
    candidate.update(overrides)
    return json.dumps({"candidates": [candidate]}, ensure_ascii=False)


class ConditionExtractionPromptTests(unittest.TestCase):
    def test_prompt_lists_only_allowed_keys_and_preserves_user_text(self) -> None:
        request = build_condition_extraction_request("서울에 살고 있고 결혼했어요")

        for key in AllowedFactKey:
            self.assertIn(key.value, request.prompt)
        self.assertIn("서울에 살고 있고 결혼했어요", request.prompt)
        self.assertIn("Never infer", request.system or "")

    def test_blank_or_oversized_user_text_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_condition_extraction_request("  ")
        with self.assertRaises(ValueError):
            build_condition_extraction_request("a" * 4001)


class ConditionExtractionContractTests(unittest.TestCase):
    def test_allowed_candidate_is_parsed(self) -> None:
        output = parse_condition_extraction(model_output())

        self.assertEqual(output.candidates[0].fact_key, AllowedFactKey.RESIDENCE_REGION)
        self.assertEqual(output.candidates[0].confidence, 0.95)

    def test_unapproved_fact_key_is_rejected(self) -> None:
        with self.assertRaises(ConditionExtractionError):
            parse_condition_extraction(model_output(factKey="BANK_TRANSACTION"))

    def test_unknown_fields_and_duplicate_keys_are_rejected(self) -> None:
        with self.assertRaises(ConditionExtractionError):
            parse_condition_extraction(model_output(secret="not-allowed"))

        candidate = json.loads(model_output())["candidates"][0]
        with self.assertRaises(ConditionExtractionError):
            parse_condition_extraction(json.dumps({"candidates": [candidate, candidate]}))

    def test_invalid_confidence_and_blank_value_are_rejected(self) -> None:
        with self.assertRaises(ConditionExtractionError):
            parse_condition_extraction(model_output(confidence=1.1))
        with self.assertRaises(ConditionExtractionError):
            parse_condition_extraction(model_output(value="  "))


class ConditionExtractionReviewTests(unittest.TestCase):
    user_text = "서울에 살고 있어요"

    def test_high_confidence_unambiguous_candidate_does_not_require_confirmation(self) -> None:
        output = parse_condition_extraction(model_output())

        result = review_condition_extraction(output, self.user_text)

        self.assertFalse(result.needs_confirmation)
        self.assertFalse(result.candidates[0].requires_confirmation)
        self.assertEqual(result.candidates[0].raw_value, "SEOUL")
        self.assertTrue(result.candidates[0].requires_normalization)
        self.assertEqual(result.conflicts, [])

    def test_low_confidence_or_ambiguous_candidate_requires_confirmation(self) -> None:
        low_confidence = review_condition_extraction(
            parse_condition_extraction(model_output(confidence=0.79)), self.user_text
        )
        ambiguous = review_condition_extraction(
            parse_condition_extraction(model_output(isAmbiguous=True)), self.user_text
        )

        self.assertTrue(low_confidence.candidates[0].requires_confirmation)
        self.assertTrue(ambiguous.candidates[0].requires_confirmation)

    def test_conflict_with_confirmed_fact_requires_resolution(self) -> None:
        output = parse_condition_extraction(model_output(value="SEOUL"))
        existing = [
            ExistingUserFact(
                fact_key=AllowedFactKey.RESIDENCE_REGION,
                value="GYEONGGI",
                confirmed=True,
            )
        ]

        result = review_condition_extraction(output, self.user_text, existing)

        self.assertTrue(result.needs_confirmation)
        self.assertTrue(result.candidates[0].requires_confirmation)
        self.assertEqual(result.conflicts[0].previous_value, "GYEONGGI")
        self.assertEqual(result.conflicts[0].candidate_value, "SEOUL")
        self.assertTrue(result.conflicts[0].resolution_required)

    def test_unconfirmed_existing_fact_does_not_create_conflict(self) -> None:
        output = parse_condition_extraction(model_output(value="SEOUL"))
        existing = [
            ExistingUserFact(
                fact_key=AllowedFactKey.RESIDENCE_REGION,
                value="GYEONGGI",
                confirmed=False,
            )
        ]

        result = review_condition_extraction(output, self.user_text, existing)

        self.assertEqual(result.conflicts, [])
        self.assertFalse(result.needs_confirmation)

    def test_same_confirmed_value_is_not_a_conflict(self) -> None:
        output = parse_condition_extraction(model_output(value=" SEOUL "))
        existing = [
            ExistingUserFact(
                fact_key=AllowedFactKey.RESIDENCE_REGION,
                value="seoul",
                confirmed=True,
            )
        ]

        result = review_condition_extraction(output, self.user_text, existing)

        self.assertEqual(result.conflicts, [])

    def test_ungrounded_evidence_requires_confirmation(self) -> None:
        output = parse_condition_extraction(
            model_output(
                factKey="MARRIAGE_STATUS",
                value="MARRIED",
                confidence=0.99,
                isAmbiguous=False,
                evidence="결혼했어요",
            )
        )

        result = review_condition_extraction(output, user_text="서울에 거주하고 있어요")

        self.assertTrue(result.needs_confirmation)
        self.assertTrue(result.candidates[0].requires_confirmation)

    def test_evidence_comparison_normalizes_whitespace_and_case(self) -> None:
        output = parse_condition_extraction(model_output(evidence="SEOUL RESIDENT"))

        result = review_condition_extraction(output, user_text="I am a  seoul\nresident.")

        self.assertFalse(result.needs_confirmation)

    def test_duplicate_confirmed_existing_facts_are_rejected(self) -> None:
        existing = [
            ExistingUserFact(
                fact_key=AllowedFactKey.RESIDENCE_REGION,
                value="SEOUL",
                confirmed=True,
            ),
            ExistingUserFact(
                fact_key=AllowedFactKey.RESIDENCE_REGION,
                value="BUSAN",
                confirmed=True,
            ),
        ]

        with self.assertRaisesRegex(ValueError, "duplicate confirmed fact: RESIDENCE_REGION"):
            review_condition_extraction(
                parse_condition_extraction(model_output()),
                self.user_text,
                existing,
            )
