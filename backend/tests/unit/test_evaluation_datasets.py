from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.modules.eligibility.rules import (
    Condition,
    EligibilityStatus,
    PolicyWindow,
    RuleEvaluationMode,
    evaluate_conditions,
)
from app.modules.user_facts.extraction import (
    AllowedFactKey,
    ConditionExtractionError,
    ExistingUserFact,
    parse_condition_extraction,
    review_condition_extraction,
)

DATASET_DIR = Path(__file__).parents[1] / "fixtures" / "evaluation"
DATASET_FILES = {
    "rule-engine-cases.json",
    "rag-retrieval-cases.json",
    "fact-extraction-cases.json",
    "e2e-scenarios.json",
    "security-cases.json",
}
REQUIRED_SCENARIO_TAGS = {
    "all_conditions_met",
    "income_unknown",
    "marriage_status_conflict",
    "application_ended",
    "available_later",
    "official_evidence_insufficient",
    "policy_source_changed",
}
ELIGIBILITY_STATUSES = {item.value for item in EligibilityStatus}
EVALUATION_STATES = {"ACTIVE", "STALE", "CONFLICTED", "NOT_EVALUATED"}


def _load(name: str) -> dict[str, Any]:
    return json.loads((DATASET_DIR / name).read_text(encoding="utf-8"))


def test_d5_dataset_manifest_and_common_contract() -> None:
    assert {path.name for path in DATASET_DIR.glob("*.json")} == DATASET_FILES

    case_ids: list[str] = []
    tags: set[str] = set()
    for name in sorted(DATASET_FILES):
        document = _load(name)
        assert document["schemaVersion"] == "1.0"
        assert isinstance(document["dataset"], str) and document["dataset"]
        assert isinstance(document["cases"], list) and document["cases"]
        for case in document["cases"]:
            assert set(case) == {"id", "title", "tags", "input", "expected"}
            assert case["id"] and case["title"]
            assert isinstance(case["tags"], list) and case["tags"]
            assert isinstance(case["input"], dict)
            assert isinstance(case["expected"], dict) and case["expected"]
            case_ids.append(case["id"])
            tags.update(case["tags"])

            status = case["expected"].get("eligibilityStatus")
            state = case["expected"].get("evaluationState")
            assert status is None or status in ELIGIBILITY_STATUSES
            assert state is None or state in EVALUATION_STATES

    assert len(case_ids) == len(set(case_ids))
    assert REQUIRED_SCENARIO_TAGS <= tags


def test_rule_engine_cases_match_current_engine_contract() -> None:
    for case in _load("rule-engine-cases.json")["cases"]:
        payload = case["input"]
        conditions = [
            Condition(
                rule_id=item["ruleId"],
                field=item["field"],
                operator=item["operator"],
                expected=item["expected"],
                required=item["required"],
                evaluation_mode=RuleEvaluationMode(
                    item.get("evaluationMode", RuleEvaluationMode.DETERMINISTIC)
                ),
            )
            for item in payload["conditions"]
        ]
        window_data = payload.get("policyWindow")
        window = None
        if window_data:
            window = PolicyWindow(
                starts_at=date.fromisoformat(window_data["startsAt"]),
                ends_at=date.fromisoformat(window_data["endsAt"]),
            )
        result = evaluate_conditions(
            conditions,
            payload["facts"],
            policy_window=window,
            evaluation_time=date.fromisoformat(payload["evaluationDate"]),
        )
        expected = case["expected"]
        assert result.eligibility_status.value == expected["eligibilityStatus"], case["id"]
        assert result.evaluation_state.value == expected["evaluationState"], case["id"]
        if "recommendationScore" in expected:
            assert result.recommendation_score == expected["recommendationScore"], case["id"]
        if "satisfiedRuleIds" in expected:
            assert [item.rule_id for item in result.satisfied] == expected["satisfiedRuleIds"], case["id"]
        if "unsatisfiedRuleIds" in expected:
            assert [item.rule_id for item in result.unsatisfied] == expected["unsatisfiedRuleIds"], case["id"]
        if "needsConfirmationRuleIds" in expected:
            assert [item.rule_id for item in result.needs_confirmation] == expected[
                "needsConfirmationRuleIds"
            ], case["id"]
        if "officialConfirmationRuleIds" in expected:
            assert [item.rule_id for item in result.official_confirmation_required] == expected[
                "officialConfirmationRuleIds"
            ], case["id"]


def test_fact_extraction_cases_use_allowlist_and_expected_review_state() -> None:
    allowed_keys = {item.value for item in AllowedFactKey}
    for case in _load("fact-extraction-cases.json")["cases"]:
        payload = case["input"]
        raw_output = json.dumps({"candidates": payload["modelCandidates"]}, ensure_ascii=False)
        if "parseError" in case["expected"]:
            with pytest.raises(ConditionExtractionError):
                parse_condition_extraction(raw_output)
            continue

        output = parse_condition_extraction(raw_output)
        existing = [
            ExistingUserFact(
                fact_key=item["factKey"], value=item["value"], confirmed=item["confirmed"]
            )
            for item in payload["existingFacts"]
        ]
        reviewed = review_condition_extraction(output, payload["userText"], existing)
        assert {item.fact_key.value for item in reviewed.candidates} <= allowed_keys
        assert [item.fact_key.value for item in reviewed.candidates] == case["expected"][
            "acceptedFactKeys"
        ]
        assert reviewed.needs_confirmation is case["expected"]["needsConfirmation"]
        conflicts = [
            {
                "factKey": item.fact_key.value,
                "previousValue": item.previous_value,
                "candidateValue": item.candidate_value,
                "resolutionRequired": item.resolution_required,
            }
            for item in reviewed.conflicts
        ]
        assert conflicts == case["expected"]["conflicts"]


def test_security_and_e2e_fixtures_contain_only_synthetic_user_values() -> None:
    serialized = json.dumps(
        [_load("security-cases.json"), _load("e2e-scenarios.json")], ensure_ascii=False
    )
    forbidden_literals = ("@gmail.com", "010-", "residentRegistrationNumber", "accessToken", "password")
    assert not any(literal in serialized for literal in forbidden_literals)
