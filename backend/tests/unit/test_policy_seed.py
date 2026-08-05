from pathlib import Path
from shutil import copytree

from app.modules.policies.csv_seed import PolicySeedError, load_policy_seed

SEED_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "policy-seed"


def test_reviewed_seed_loads_as_a_linked_catalog() -> None:
    catalog = load_policy_seed(SEED_DIRECTORY)

    assert len(catalog.categories) == 5
    assert len(catalog.policies) == 38
    assert len(catalog.questions) == 49
    assert len(catalog.rules) == 133
    assert len(catalog.relations) == 24
    assert len(catalog.rag_documents()) == 38
    assert {document.policy_id for document in catalog.rag_documents()} == set(catalog.policies)


def test_placeholder_thresholds_are_excluded_from_deterministic_rules() -> None:
    catalog = load_policy_seed(SEED_DIRECTORY)

    deterministic = tuple(
        rule for policy_id in catalog.policies for rule in catalog.deterministic_rules(policy_id)
    )
    confirmation_required = tuple(
        rule
        for policy_id in catalog.policies
        for rule in catalog.confirmation_required_rules(policy_id)
    )

    assert len(deterministic) == 110
    assert len(confirmation_required) == 23
    assert all(rule.requires_official_confirmation for rule in confirmation_required)


def test_missing_required_file_is_rejected(tmp_path: Path) -> None:
    try:
        load_policy_seed(tmp_path)
    except PolicySeedError as exc:
        assert "SHA256SUMS" in str(exc)
    else:
        raise AssertionError("missing seed file should be rejected")


def test_changed_seed_file_is_rejected(tmp_path: Path) -> None:
    copied_seed = tmp_path / "policy-seed"
    copytree(SEED_DIRECTORY, copied_seed)
    with (copied_seed / "02_policy.csv").open("a", encoding="utf-8") as target:
        target.write("\n")

    try:
        load_policy_seed(copied_seed)
    except PolicySeedError as exc:
        assert "checksum mismatch" in str(exc)
    else:
        raise AssertionError("changed seed file should be rejected")
