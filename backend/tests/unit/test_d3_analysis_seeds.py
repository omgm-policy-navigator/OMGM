import csv
from pathlib import Path

SEED_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "policy-seed"


def _rows(filename: str) -> list[dict[str, str]]:
    with (SEED_DIRECTORY / filename).open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def test_rule_candidate_seed_preserves_reviewed_rules_and_provenance() -> None:
    canonical = _rows("03_policy_rule.csv")
    candidates = _rows("policy_rule_seed.csv")

    assert len(candidates) == len(canonical) == 133
    assert {row["id"] for row in candidates} == {row["id"] for row in canonical}
    for row in candidates:
        assert row["evidence_text"].strip()
        assert row["source_url"].startswith(("http://", "https://"))
        assert row["source_location"].startswith("03_policy_rule.csv#row:")
        assert row["extraction_method"] == "REVIEWED_CSV_BASELINE"
        assert row["admin_review_status"] in {"APPROVED", "NEEDS_OFFICIAL_CONFIRMATION"}


def test_hard_to_express_rules_remain_official_confirmation_required() -> None:
    candidates = _rows("policy_rule_seed.csv")
    confirmation_required = [
        row for row in candidates if row["admin_review_status"] == "NEEDS_OFFICIAL_CONFIRMATION"
    ]

    assert len(confirmation_required) == 31
    assert all(row["evaluation_mode"] == "OFFICIAL_CONFIRMATION_REQUIRED" for row in confirmation_required)


def test_question_seed_matches_reviewed_question_baseline() -> None:
    canonical = _rows("04_question.csv")
    questions = _rows("question_seed.csv")

    assert len(questions) == len(canonical) == 49
    assert {row["id"] for row in questions} == {row["id"] for row in canonical}
    assert all(row["condition_key"].strip() for row in questions)
    assert all(row["question_text"].strip() for row in questions)
    assert all(row["admin_review_status"] == "APPROVED" for row in questions)


def test_relation_seed_matches_reviewed_relation_baseline() -> None:
    canonical = _rows("07_policy_relation.csv")
    relations = _rows("policy_relation_seed.csv")

    assert len(relations) == len(canonical) == 24
    assert {row["id"] for row in relations} == {row["id"] for row in canonical}
    assert all(row["description"].strip() for row in relations)
    assert all(row["admin_review_status"] == "APPROVED" for row in relations)
