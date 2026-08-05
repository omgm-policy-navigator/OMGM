import csv
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from shutil import copytree

import pytest

from app.modules.policies.csv_seed import (
    EvaluationMode,
    PolicySeedError,
    RuleOperator,
    RuleReviewStatus,
    load_policy_seed,
)

SEED_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "policy-seed"


def _copy_seed(tmp_path: Path) -> Path:
    return Path(copytree(SEED_DIRECTORY, tmp_path / "policy-seed"))


def _update_checksum(seed: Path, filename: str) -> None:
    path = seed / filename
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    checksum = hashlib.sha256(normalized).hexdigest()
    manifest = seed / "SHA256SUMS"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    manifest.write_text(
        "\n".join(
            f"{checksum}  {filename}" if line.endswith(f"  {filename}") else line
            for line in lines
        )
        + "\n",
        encoding="utf-8",
    )


def _rewrite_csv(seed: Path, filename: str, mutate: Callable[[list[dict[str, str]]], None]) -> None:
    path = seed / filename
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    _update_checksum(seed, filename)


def test_reviewed_seed_loads_as_a_linked_catalog() -> None:
    catalog = load_policy_seed(SEED_DIRECTORY)

    assert len(catalog.categories) == 5
    assert len(catalog.policies) == 38
    assert len(catalog.questions) == 49
    assert len(catalog.rules) == 133
    assert len(catalog.relations) == 24
    assert len(catalog.rag_documents()) == 38
    assert {document.policy_id for document in catalog.rag_documents()} == set(catalog.policies)


def test_question_options_expose_labels_and_canonical_values() -> None:
    catalog = load_policy_seed(SEED_DIRECTORY)

    options = {option.label: option.value for option in catalog.questions["2"].options}

    assert options["결혼 예정"] == "PRE_MARRIED"
    assert options["혼인신고 완료"] == "MARRIED"


def test_every_deterministic_rule_value_is_reachable_from_question_options() -> None:
    catalog = load_policy_seed(SEED_DIRECTORY)

    for rule in catalog.rules:
        question = catalog.questions[rule.question_id]
        if rule.evaluation_mode is not EvaluationMode.DETERMINISTIC or not question.options:
            continue
        option_values = {option.value for option in question.options}
        if rule.operator is RuleOperator.IN:
            assert set(rule.expected_value.split("|")) <= option_values
        elif rule.operator in {RuleOperator.EQ, RuleOperator.CONTAINS, RuleOperator.NOT_CONTAINS}:
            assert rule.expected_value in option_values


def test_confirmation_mode_is_explicit_and_not_inferred_from_placeholder_name() -> None:
    catalog = load_policy_seed(SEED_DIRECTORY)
    deterministic = tuple(
        rule for policy_id in catalog.policies for rule in catalog.deterministic_rules(policy_id)
    )
    confirmation_required = tuple(
        rule
        for policy_id in catalog.policies
        for rule in catalog.confirmation_required_rules(policy_id)
    )

    assert len(deterministic) == 102
    assert len(confirmation_required) == 31
    assert all(rule.review_status is RuleReviewStatus.APPROVED for rule in deterministic)
    assert all(rule.review_status is RuleReviewStatus.DRAFT for rule in confirmation_required)
    application_period_rule = next(
        rule for rule in catalog.rules if rule.expected_value == "APPLICATION_PERIOD"
    )
    assert application_period_rule.requires_official_confirmation


def test_show_condition_uses_validated_canonical_values() -> None:
    catalog = load_policy_seed(SEED_DIRECTORY)
    condition = catalog.questions["50"].show_condition

    assert condition is not None
    assert condition.condition_key == "PREGNANCY_OR_POSTPARTUM"
    assert condition.operator.value == "EQ"
    assert condition.value == "POSTPARTUM"


def test_invalid_show_condition_shape_is_rejected(tmp_path: Path) -> None:
    seed = _copy_seed(tmp_path)

    def mutate(rows: list[dict[str, str]]) -> None:
        next(row for row in rows if row["id"] == "50")["show_condition"] = json.dumps(
            {"condition_key": "PREGNANCY_OR_POSTPARTUM", "EQ": "POSTPARTUM"}
        )

    _rewrite_csv(seed, "04_question.csv", mutate)

    with pytest.raises(PolicySeedError, match="condition_key, operator, and value"):
        load_policy_seed(seed)


def test_invalid_required_boolean_is_rejected(tmp_path: Path) -> None:
    seed = _copy_seed(tmp_path)

    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0]["required"] = "treu"

    _rewrite_csv(seed, "03_policy_rule.csv", mutate)

    with pytest.raises(PolicySeedError, match="must be either true or false"):
        load_policy_seed(seed)


def test_missing_required_header_is_rejected(tmp_path: Path) -> None:
    seed = _copy_seed(tmp_path)
    path = seed / "02_policy.csv"
    content = path.read_text(encoding="utf-8-sig").replace("application_url", "application_link", 1)
    path.write_text(content, encoding="utf-8-sig")
    _update_checksum(seed, "02_policy.csv")

    with pytest.raises(PolicySeedError, match="02_policy.csv is missing columns: application_url"):
        load_policy_seed(seed)


def test_unsupported_enum_value_is_rejected(tmp_path: Path) -> None:
    seed = _copy_seed(tmp_path)

    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0]["operator"] = "BETWEN"

    _rewrite_csv(seed, "03_policy_rule.csv", mutate)

    with pytest.raises(PolicySeedError, match="rule 1.operator has unsupported value"):
        load_policy_seed(seed)


def test_draft_rule_cannot_enter_deterministic_evaluation(tmp_path: Path) -> None:
    seed = _copy_seed(tmp_path)

    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0]["review_status"] = "DRAFT"

    _rewrite_csv(seed, "03_policy_rule.csv", mutate)

    with pytest.raises(PolicySeedError, match="Deterministic rule 1 must be APPROVED"):
        load_policy_seed(seed)


def test_invalid_or_reversed_policy_dates_are_rejected(tmp_path: Path) -> None:
    invalid_seed = _copy_seed(tmp_path / "invalid")

    def invalid_date(rows: list[dict[str, str]]) -> None:
        rows[0]["verified_at"] = "2026-13-45"

    _rewrite_csv(invalid_seed, "02_policy.csv", invalid_date)
    with pytest.raises(PolicySeedError, match="must use YYYY-MM-DD"):
        load_policy_seed(invalid_seed)

    reversed_seed = _copy_seed(tmp_path / "reversed")

    def reversed_dates(rows: list[dict[str, str]]) -> None:
        rows[0]["application_start_date"] = "2026-12-31"
        rows[0]["application_end_date"] = "2026-01-01"

    _rewrite_csv(reversed_seed, "02_policy.csv", reversed_dates)
    with pytest.raises(PolicySeedError, match="start date is after end date"):
        load_policy_seed(reversed_seed)


def test_missing_required_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PolicySeedError, match="SHA256SUMS"):
        load_policy_seed(tmp_path)


def test_changed_seed_file_is_rejected(tmp_path: Path) -> None:
    seed = _copy_seed(tmp_path)
    with (seed / "02_policy.csv").open("a", encoding="utf-8") as target:
        target.write("\n")

    with pytest.raises(PolicySeedError, match="checksum mismatch"):
        load_policy_seed(seed)


def test_seed_checksums_are_portable_across_line_endings(tmp_path: Path) -> None:
    seed = _copy_seed(tmp_path)
    for path in seed.iterdir():
        if path.name != "SHA256SUMS":
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))

    catalog = load_policy_seed(seed)

    assert len(catalog.policies) == 38
