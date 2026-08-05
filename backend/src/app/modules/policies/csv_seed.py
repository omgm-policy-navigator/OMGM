from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, TypeVar
from urllib.parse import urlparse


class PolicySeedError(ValueError):
    """Raised when the versioned policy seed violates its contract."""


class HasId(Protocol):
    id: str


CatalogItem = TypeVar("CatalogItem", bound=HasId)


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class Policy:
    id: str
    category_id: str
    name: str
    summary: str
    managing_agency: str
    application_url: str
    application_start_date: str | None
    application_end_date: str | None
    status: str
    source_url: str
    verified_at: str


@dataclass(frozen=True)
class Question:
    id: str
    category_id: str
    condition_key: str
    question_text: str
    answer_type: str
    options: tuple[str, ...]
    priority: int
    parent_question_id: str | None
    show_condition: Mapping[str, object] | None


@dataclass(frozen=True)
class PolicyRule:
    id: str
    policy_id: str
    condition_key: str
    operator: str
    expected_value: str
    required: bool
    question_id: str
    source_text: str

    @property
    def requires_official_confirmation(self) -> bool:
        value = self.expected_value.upper()
        return "OFFICIAL" in value or "ANNOUNCEMENT" in value


@dataclass(frozen=True)
class PolicyRelation:
    id: str
    from_policy_id: str
    to_policy_id: str
    relation_type: str
    description: str


@dataclass(frozen=True)
class RagDocument:
    id: str
    policy_id: str
    document_type: str
    title: str
    content: str
    source_url: str


@dataclass(frozen=True)
class PolicySeedCatalog:
    categories: Mapping[str, Category]
    policies: Mapping[str, Policy]
    questions: Mapping[str, Question]
    rules: tuple[PolicyRule, ...]
    relations: tuple[PolicyRelation, ...]
    documents: tuple[RagDocument, ...]

    def deterministic_rules(self, policy_id: str) -> tuple[PolicyRule, ...]:
        return tuple(
            rule
            for rule in self.rules
            if rule.policy_id == policy_id and not rule.requires_official_confirmation
        )

    def confirmation_required_rules(self, policy_id: str) -> tuple[PolicyRule, ...]:
        return tuple(
            rule
            for rule in self.rules
            if rule.policy_id == policy_id and rule.requires_official_confirmation
        )

    def rag_documents(self) -> tuple[RagDocument, ...]:
        return self.documents


def _verify_checksums(directory: Path) -> None:
    manifest = directory / "SHA256SUMS"
    if not manifest.is_file():
        raise PolicySeedError("Required policy seed file is missing: SHA256SUMS")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, filename = line.split(maxsplit=1)
        path = directory / filename.strip()
        if not path.is_file():
            raise PolicySeedError(f"Checksummed policy seed file is missing: {filename.strip()}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise PolicySeedError(f"Policy seed checksum mismatch: {filename.strip()}")


def _read_rows(directory: Path, filename: str) -> list[dict[str, str]]:
    path = directory / filename
    if not path.is_file():
        raise PolicySeedError(f"Required policy seed file is missing: {filename}")
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _optional(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _mapping(items: list[CatalogItem], entity_name: str) -> Mapping[str, CatalogItem]:
    result: dict[str, CatalogItem] = {}
    for item in items:
        item_id = item.id
        if item_id in result:
            raise PolicySeedError(f"Duplicate {entity_name} id: {item_id}")
        result[item_id] = item
    return MappingProxyType(result)


def _json_list(value: str, field: str) -> tuple[str, ...]:
    if not value.strip():
        return ()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise PolicySeedError(f"Invalid JSON in {field}") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise PolicySeedError(f"{field} must be a JSON string array")
    return tuple(parsed)


def _json_object(value: str, field: str) -> Mapping[str, object] | None:
    if not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise PolicySeedError(f"Invalid JSON in {field}") from exc
    if not isinstance(parsed, dict):
        raise PolicySeedError(f"{field} must be a JSON object")
    return MappingProxyType(parsed)


def _require_http_url(value: str, field: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PolicySeedError(f"{field} must be an HTTP(S) URL")
    return value


def _require_references(catalog: PolicySeedCatalog) -> None:
    for policy in catalog.policies.values():
        if policy.category_id not in catalog.categories:
            raise PolicySeedError(f"Policy {policy.id} references an unknown category")
    for question in catalog.questions.values():
        if question.category_id not in catalog.categories:
            raise PolicySeedError(f"Question {question.id} references an unknown category")
        if question.parent_question_id and question.parent_question_id not in catalog.questions:
            raise PolicySeedError(f"Question {question.id} references an unknown parent question")
    for rule in catalog.rules:
        if rule.policy_id not in catalog.policies or rule.question_id not in catalog.questions:
            raise PolicySeedError(f"Rule {rule.id} has an unknown policy or question")
    for relation in catalog.relations:
        if relation.from_policy_id not in catalog.policies or relation.to_policy_id not in catalog.policies:
            raise PolicySeedError(f"Relation {relation.id} references an unknown policy")
    for document in catalog.documents:
        if document.policy_id not in catalog.policies:
            raise PolicySeedError(f"Document {document.id} references an unknown policy")

    documented_policy_ids = {document.policy_id for document in catalog.documents}
    missing = set(catalog.policies) - documented_policy_ids
    if missing:
        raise PolicySeedError(f"Policies without a RAG document: {', '.join(sorted(missing))}")


def load_policy_seed(directory: Path) -> PolicySeedCatalog:
    directory = directory.resolve()
    _verify_checksums(directory)
    categories = [
        Category(id=row["id"], name=row["name"], description=row["description"])
        for row in _read_rows(directory, "01_category.csv")
    ]
    policies = [
        Policy(
            id=row["id"],
            category_id=row["category_id"],
            name=row["name"],
            summary=row["summary"],
            managing_agency=row["managing_agency"],
            application_url=_require_http_url(row["application_url"], "policy.application_url"),
            application_start_date=_optional(row["application_start_date"]),
            application_end_date=_optional(row["application_end_date"]),
            status=row["status"],
            source_url=_require_http_url(row["source_url"], "policy.source_url"),
            verified_at=row["verified_at"],
        )
        for row in _read_rows(directory, "02_policy.csv")
    ]
    questions = [
        Question(
            id=row["id"],
            category_id=row["category_id"],
            condition_key=row["condition_key"],
            question_text=row["question_text"],
            answer_type=row["answer_type"],
            options=_json_list(row["options"], f"question {row['id']}.options"),
            priority=int(row["priority"]),
            parent_question_id=_optional(row["parent_question_id"]),
            show_condition=_json_object(row["show_condition"], f"question {row['id']}.show_condition"),
        )
        for row in _read_rows(directory, "04_question.csv")
    ]
    rules = tuple(
        PolicyRule(
            id=row["id"],
            policy_id=row["policy_id"],
            condition_key=row["condition_key"],
            operator=row["operator"],
            expected_value=row["expected_value"],
            required=row["required"].strip().lower() == "true",
            question_id=row["question_id"],
            source_text=row["source_text"],
        )
        for row in _read_rows(directory, "03_policy_rule.csv")
    )
    relations = tuple(
        PolicyRelation(**row) for row in _read_rows(directory, "07_policy_relation.csv")
    )
    documents = tuple(
        RagDocument(
            id=row["id"],
            policy_id=row["policy_id"],
            document_type=row["document_type"],
            title=row["title"],
            content=row["content"],
            source_url=_require_http_url(row["source_url"], "policy_document.source_url"),
        )
        for row in _read_rows(directory, "08_policy_document.csv")
    )
    catalog = PolicySeedCatalog(
        categories=_mapping(categories, "category"),
        policies=_mapping(policies, "policy"),
        questions=_mapping(questions, "question"),
        rules=rules,
        relations=relations,
        documents=documents,
    )
    _require_references(catalog)
    return catalog
