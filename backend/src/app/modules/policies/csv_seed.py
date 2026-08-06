from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, TypeVar
from urllib.parse import urlparse


class PolicySeedError(ValueError):
    """Raised when the versioned policy seed violates its contract."""


class PolicyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RECRUITMENT_BASED = "RECRUITMENT_BASED"
    PERIODIC = "PERIODIC"
    PILOT_OR_BUDGET_LIMITED = "PILOT_OR_BUDGET_LIMITED"
    BUDGET_LIMITED = "BUDGET_LIMITED"


class AnswerType(StrEnum):
    SINGLE_SELECT = "SINGLE_SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    NUMBER = "NUMBER"
    MONEY = "MONEY"


class RuleOperator(StrEnum):
    EQ = "EQ"
    IN = "IN"
    LT = "LT"
    LTE = "LTE"
    GTE = "GTE"
    BETWEEN = "BETWEEN"
    IN_PERIOD = "IN_PERIOD"
    IN_TAX_YEAR = "IN_TAX_YEAR"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    ANY = "ANY"


class RelationType(StrEnum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    RELATED = "RELATED"
    ALTERNATIVE = "ALTERNATIVE"
    CONFLICT = "CONFLICT"
    REEVALUATE_AFTER = "REEVALUATE_AFTER"


class DocumentType(StrEnum):
    OVERVIEW = "OVERVIEW"


class EvaluationMode(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    OFFICIAL_CONFIRMATION_REQUIRED = "OFFICIAL_CONFIRMATION_REQUIRED"


class RuleReviewStatus(StrEnum):
    APPROVED = "APPROVED"
    DRAFT = "DRAFT"


class ShowOperator(StrEnum):
    EQ = "EQ"
    NE = "NE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    CONTAINS = "CONTAINS"


class HasId(Protocol):
    id: str


CatalogItem = TypeVar("CatalogItem", bound=HasId)
EnumValue = TypeVar("EnumValue", bound=StrEnum)


REQUIRED_COLUMNS = {
    "01_category.csv": {"id", "name", "code", "description", "display_order"},
    "02_policy.csv": {
        "id",
        "category_id",
        "name",
        "summary",
        "managing_agency",
        "application_url",
        "application_start_date",
        "application_end_date",
        "status",
        "source_url",
        "verified_at",
    },
    "03_policy_rule.csv": {
        "id",
        "policy_id",
        "condition_key",
        "operator",
        "expected_value",
        "required",
        "question_id",
        "source_text",
        "evaluation_mode",
        "review_status",
    },
    "04_question.csv": {
        "id",
        "category_id",
        "condition_key",
        "question_text",
        "answer_type",
        "options",
        "priority",
        "parent_question_id",
        "show_condition",
    },
    "07_policy_relation.csv": {
        "id",
        "from_policy_id",
        "to_policy_id",
        "relation_type",
        "description",
    },
    "08_policy_document.csv": {
        "id",
        "policy_id",
        "document_type",
        "title",
        "content",
        "source_url",
        "embedding",
    },
}


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
    application_start_date: date | None
    application_end_date: date | None
    status: PolicyStatus
    source_url: str
    verified_at: date


@dataclass(frozen=True)
class QuestionOption:
    label: str
    value: str


@dataclass(frozen=True)
class ShowCondition:
    condition_key: str
    operator: ShowOperator
    value: object


@dataclass(frozen=True)
class Question:
    id: str
    category_id: str
    condition_key: str
    question_text: str
    answer_type: AnswerType
    options: tuple[QuestionOption, ...]
    priority: int
    parent_question_id: str | None
    show_condition: ShowCondition | None


@dataclass(frozen=True)
class PolicyRule:
    id: str
    policy_id: str
    condition_key: str
    operator: RuleOperator
    expected_value: str
    required: bool
    question_id: str
    source_text: str
    evaluation_mode: EvaluationMode
    review_status: RuleReviewStatus

    @property
    def requires_official_confirmation(self) -> bool:
        return self.evaluation_mode is EvaluationMode.OFFICIAL_CONFIRMATION_REQUIRED


@dataclass(frozen=True)
class PolicyRelation:
    id: str
    from_policy_id: str
    to_policy_id: str
    relation_type: RelationType
    description: str


@dataclass(frozen=True)
class RagDocument:
    id: str
    policy_id: str
    document_type: DocumentType
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
            if rule.policy_id == policy_id
            and rule.evaluation_mode is EvaluationMode.DETERMINISTIC
            and rule.review_status is RuleReviewStatus.APPROVED
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
        try:
            expected, filename = line.split(maxsplit=1)
        except ValueError as exc:
            raise PolicySeedError("SHA256SUMS contains an invalid entry") from exc
        path = directory / filename.strip()
        if not path.is_file():
            raise PolicySeedError(f"Checksummed policy seed file is missing: {filename.strip()}")
        normalized_bytes = path.read_bytes().replace(b"\r\n", b"\n")
        actual = hashlib.sha256(normalized_bytes).hexdigest()
        if actual != expected:
            raise PolicySeedError(f"Policy seed checksum mismatch: {filename.strip()}")


def _read_rows(directory: Path, filename: str) -> list[dict[str, str]]:
    path = directory / filename
    if not path.is_file():
        raise PolicySeedError(f"Required policy seed file is missing: {filename}")
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        actual_columns = set(reader.fieldnames or ())
        expected_columns = REQUIRED_COLUMNS[filename]
        missing = expected_columns - actual_columns
        unexpected = actual_columns - expected_columns
        if missing:
            raise PolicySeedError(f"{filename} is missing columns: {', '.join(sorted(missing))}")
        if unexpected:
            raise PolicySeedError(f"{filename} contains unknown columns: {', '.join(sorted(unexpected))}")
        return list(reader)


def _optional(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _require_text(value: str, field: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise PolicySeedError(f"{field} must not be empty")
    return stripped


def _require_bool(value: str, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise PolicySeedError(f"{field} must be either true or false")


def _require_enum(enum_type: type[EnumValue], value: str, field: str) -> EnumValue:
    try:
        return enum_type(value.strip())
    except ValueError as exc:
        raise PolicySeedError(f"{field} has unsupported value: {value}") from exc


def _optional_date(value: str, field: str) -> date | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return date.fromisoformat(stripped)
    except ValueError as exc:
        raise PolicySeedError(f"{field} must use YYYY-MM-DD") from exc


def _required_date(value: str, field: str) -> date:
    parsed = _optional_date(value, field)
    if parsed is None:
        raise PolicySeedError(f"{field} must not be empty")
    return parsed


def _mapping(items: list[CatalogItem], entity_name: str) -> Mapping[str, CatalogItem]:
    result: dict[str, CatalogItem] = {}
    for item in items:
        if item.id in result:
            raise PolicySeedError(f"Duplicate {entity_name} id: {item.id}")
        result[item.id] = item
    return MappingProxyType(result)


def _question_options(value: str, field: str) -> tuple[QuestionOption, ...]:
    if not value.strip():
        return ()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise PolicySeedError(f"Invalid JSON in {field}") from exc
    if not isinstance(parsed, list):
        raise PolicySeedError(f"{field} must be a JSON object array")
    options: list[QuestionOption] = []
    for item in parsed:
        if not isinstance(item, dict) or set(item) != {"label", "value"}:
            raise PolicySeedError(f"{field} entries must contain exactly label and value")
        options.append(
            QuestionOption(
                label=_require_text(str(item["label"]), f"{field}.label"),
                value=_require_text(str(item["value"]), f"{field}.value"),
            )
        )
    if len({option.value for option in options}) != len(options):
        raise PolicySeedError(f"{field} contains duplicate canonical values")
    return tuple(options)


def _show_condition(value: str, field: str) -> ShowCondition | None:
    if not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise PolicySeedError(f"Invalid JSON in {field}") from exc
    if not isinstance(parsed, dict) or set(parsed) != {"condition_key", "operator", "value"}:
        raise PolicySeedError(f"{field} must contain exactly condition_key, operator, and value")
    return ShowCondition(
        condition_key=_require_text(str(parsed["condition_key"]), f"{field}.condition_key"),
        operator=_require_enum(ShowOperator, str(parsed["operator"]), f"{field}.operator"),
        value=parsed["value"],
    )


def _require_http_url(value: str, field: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PolicySeedError(f"{field} must be an HTTP(S) URL")
    return value


def _policy(row: dict[str, str]) -> Policy:
    policy_id = row["id"]
    start = _optional_date(row["application_start_date"], f"policy {policy_id}.application_start_date")
    end = _optional_date(row["application_end_date"], f"policy {policy_id}.application_end_date")
    if start is not None and end is not None and start > end:
        raise PolicySeedError(f"Policy {policy_id} start date is after end date")
    return Policy(
        id=policy_id,
        category_id=row["category_id"],
        name=row["name"],
        summary=row["summary"],
        managing_agency=row["managing_agency"],
        application_url=_require_http_url(row["application_url"], f"policy {policy_id}.application_url"),
        application_start_date=start,
        application_end_date=end,
        status=_require_enum(PolicyStatus, row["status"], f"policy {policy_id}.status"),
        source_url=_require_http_url(row["source_url"], f"policy {policy_id}.source_url"),
        verified_at=_required_date(row["verified_at"], f"policy {policy_id}.verified_at"),
    )


def _expected_option_values(rule: PolicyRule) -> set[str] | None:
    if rule.operator is RuleOperator.IN:
        return set(rule.expected_value.split("|"))
    if rule.operator in {RuleOperator.EQ, RuleOperator.CONTAINS, RuleOperator.NOT_CONTAINS}:
        return {rule.expected_value}
    return None


def _require_references(catalog: PolicySeedCatalog) -> None:
    questions_by_key = {question.condition_key: question for question in catalog.questions.values()}
    for policy in catalog.policies.values():
        if policy.category_id not in catalog.categories:
            raise PolicySeedError(f"Policy {policy.id} references an unknown category")
    for question in catalog.questions.values():
        if question.category_id not in catalog.categories:
            raise PolicySeedError(f"Question {question.id} references an unknown category")
        if question.parent_question_id and question.parent_question_id not in catalog.questions:
            raise PolicySeedError(f"Question {question.id} references an unknown parent question")
        condition = question.show_condition
        if condition is not None:
            referenced = questions_by_key.get(condition.condition_key)
            if referenced is None:
                raise PolicySeedError(f"Question {question.id} show_condition references an unknown condition_key")
            if referenced.options:
                allowed = {option.value for option in referenced.options}
                values = condition.value if isinstance(condition.value, list) else [condition.value]
                if any(value not in allowed for value in values):
                    raise PolicySeedError(f"Question {question.id} show_condition contains an unknown option value")
    for rule in catalog.rules:
        if rule.policy_id not in catalog.policies or rule.question_id not in catalog.questions:
            raise PolicySeedError(f"Rule {rule.id} has an unknown policy or question")
        question = catalog.questions[rule.question_id]
        if question.condition_key != rule.condition_key:
            raise PolicySeedError(f"Rule {rule.id} condition_key does not match question {question.id}")
        expected = _expected_option_values(rule)
        if rule.evaluation_mode is EvaluationMode.DETERMINISTIC and rule.review_status is not RuleReviewStatus.APPROVED:
            raise PolicySeedError(f"Deterministic rule {rule.id} must be APPROVED")
        if rule.review_status is RuleReviewStatus.APPROVED and question.options and expected is not None:
            available = {option.value for option in question.options}
            if not expected <= available:
                raise PolicySeedError(f"Rule {rule.id} expected value is not reachable from question options")
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
    policies = [_policy(row) for row in _read_rows(directory, "02_policy.csv")]
    questions = [
        Question(
            id=row["id"],
            category_id=row["category_id"],
            condition_key=row["condition_key"],
            question_text=row["question_text"],
            answer_type=_require_enum(AnswerType, row["answer_type"], f"question {row['id']}.answer_type"),
            options=_question_options(row["options"], f"question {row['id']}.options"),
            priority=int(row["priority"]),
            parent_question_id=_optional(row["parent_question_id"]),
            show_condition=_show_condition(row["show_condition"], f"question {row['id']}.show_condition"),
        )
        for row in _read_rows(directory, "04_question.csv")
    ]
    rules = tuple(
        PolicyRule(
            id=row["id"],
            policy_id=row["policy_id"],
            condition_key=row["condition_key"],
            operator=_require_enum(RuleOperator, row["operator"], f"rule {row['id']}.operator"),
            expected_value=row["expected_value"],
            required=_require_bool(row["required"], f"rule {row['id']}.required"),
            question_id=row["question_id"],
            source_text=row["source_text"],
            evaluation_mode=_require_enum(
                EvaluationMode, row["evaluation_mode"], f"rule {row['id']}.evaluation_mode"
            ),
            review_status=_require_enum(
                RuleReviewStatus, row["review_status"], f"rule {row['id']}.review_status"
            ),
        )
        for row in _read_rows(directory, "03_policy_rule.csv")
    )
    relations = tuple(
        PolicyRelation(
            id=row["id"],
            from_policy_id=row["from_policy_id"],
            to_policy_id=row["to_policy_id"],
            relation_type=_require_enum(RelationType, row["relation_type"], f"relation {row['id']}.relation_type"),
            description=row["description"],
        )
        for row in _read_rows(directory, "07_policy_relation.csv")
    )
    documents = tuple(
        RagDocument(
            id=row["id"],
            policy_id=row["policy_id"],
            document_type=_require_enum(DocumentType, row["document_type"], f"document {row['id']}.document_type"),
            title=row["title"],
            content=row["content"],
            source_url=_require_http_url(row["source_url"], f"document {row['id']}.source_url"),
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
