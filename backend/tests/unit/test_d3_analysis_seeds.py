import csv
import hashlib
from collections import Counter
from pathlib import Path

SEED_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "policy-seed"


def _rows(filename: str) -> list[dict[str, str]]:
    with (SEED_DIRECTORY / filename).open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["id"]: row for row in rows}


def _normalized_digest(path: Path) -> str:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def test_rule_seed_preserves_canonical_rule_contract() -> None:
    canonical = _by_id(_rows("03_policy_rule.csv"))
    candidates = _by_id(_rows("policy_rule_seed.csv"))

    assert len(candidates) == len(canonical) == 133
    assert candidates.keys() == canonical.keys()
    preserved_fields = (
        "policy_id",
        "condition_key",
        "operator",
        "expected_value",
        "required",
        "question_id",
    )
    for rule_id, source in canonical.items():
        candidate = candidates[rule_id]
        for field in preserved_fields:
            assert candidate[field] == source[field], f"rule {rule_id}: {field} mismatch"


def test_rules_without_official_location_require_confirmation() -> None:
    candidates = _rows("policy_rule_seed.csv")
    allowed_pairs = {
        ("APPROVED", "DETERMINISTIC"),
        ("NEEDS_OFFICIAL_CONFIRMATION", "OFFICIAL_CONFIRMATION_REQUIRED"),
    }

    for row in candidates:
        assert row["evidence_text"].strip()
        assert row["source_url"].startswith(("http://", "https://"))
        assert row["baseline_source_location"].startswith("03_policy_rule.csv#row:")
        assert row["extraction_method"] == "REVIEWED_CSV_BASELINE"
        assert (row["admin_review_status"], row["evaluation_mode"]) in allowed_pairs
        if row["admin_review_status"] == "APPROVED":
            assert row["official_source_location"].strip()
            assert not row["official_source_location"].startswith("03_policy_rule.csv")
        if not row["official_source_location"].strip():
            assert row["admin_review_status"] == "NEEDS_OFFICIAL_CONFIRMATION"
            assert row["evaluation_mode"] == "OFFICIAL_CONFIRMATION_REQUIRED"

    assert sum(row["admin_review_status"] == "APPROVED" for row in candidates) == 0
    assert sum(row["admin_review_status"] == "NEEDS_OFFICIAL_CONFIRMATION" for row in candidates) == 133


def test_question_seed_preserves_canonical_question_contract() -> None:
    canonical = _by_id(_rows("04_question.csv"))
    questions = _by_id(_rows("question_seed.csv"))

    assert len(questions) == len(canonical) == 49
    assert questions.keys() == canonical.keys()
    for question_id, source in canonical.items():
        candidate = questions[question_id]
        for field in ("condition_key", "question_text"):
            assert candidate[field] == source[field], f"question {question_id}: {field} mismatch"
        assert candidate["admin_review_status"] == "APPROVED"


def test_relation_seed_preserves_canonical_relation_contract() -> None:
    canonical = _by_id(_rows("07_policy_relation.csv"))
    relations = _by_id(_rows("policy_relation_seed.csv"))

    assert len(relations) == len(canonical) == 24
    assert relations.keys() == canonical.keys()
    for relation_id, source in canonical.items():
        candidate = relations[relation_id]
        for field in ("from_policy_id", "to_policy_id", "relation_type", "description"):
            assert candidate[field] == source[field], f"relation {relation_id}: {field} mismatch"


def test_relations_without_official_evidence_require_confirmation() -> None:
    relations = _rows("policy_relation_seed.csv")
    uncertain_phrases = ("여부 확인", "확인 필요", "공고 확인", "은행 확인")

    for relation in relations:
        assert relation["evidence_text"].strip()
        assert relation["from_source_url"].startswith(("http://", "https://"))
        assert relation["to_source_url"].startswith(("http://", "https://"))
        assert relation["baseline_source_location"].startswith("07_policy_relation.csv#row:")
        if any(phrase in relation["description"] for phrase in uncertain_phrases):
            assert relation["admin_review_status"] == "NEEDS_OFFICIAL_CONFIRMATION"
        if not (
            relation["from_official_source_location"].strip()
            and relation["to_official_source_location"].strip()
        ):
            assert relation["admin_review_status"] == "NEEDS_OFFICIAL_CONFIRMATION"

    assert all(row["admin_review_status"] == "NEEDS_OFFICIAL_CONFIRMATION" for row in relations)


def test_checksum_manifest_has_unique_filenames_and_matches_seed_files() -> None:
    lines = (SEED_DIRECTORY / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    entries = [line.split(maxsplit=1) for line in lines if line.strip()]
    filenames = [filename.strip() for _, filename in entries]
    duplicates = {name for name, count in Counter(filenames).items() if count > 1}

    assert duplicates == set()
    for expected_hash, filename in entries:
        path = SEED_DIRECTORY / filename.strip()
        assert path.exists()
        assert _normalized_digest(path) == expected_hash
