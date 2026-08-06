from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ShowCondition:
    fact_key: str
    equals: Any


@dataclass(frozen=True)
class QuestionTemplate:
    question_id: str
    category_code: str
    fact_key: str
    prompt: str
    answer_type: str
    required: bool
    priority: int
    discriminator_score: int
    parent_question_id: str | None = None
    show_condition: ShowCondition | None = None
    options: tuple[str, ...] = ()


QUESTION_BANK: tuple[QuestionTemplate, ...] = (
    QuestionTemplate(
        "q_housing_region",
        "housing",
        "region",
        "Which region do you currently live in?",
        "single_select",
        True,
        10,
        100,
        options=("Seoul", "Gyeonggi", "Incheon", "Busan", "National"),
    ),
    QuestionTemplate(
        "q_housing_marital_status",
        "housing",
        "marital_status",
        "What is your current marriage status?",
        "single_select",
        True,
        20,
        95,
        options=("engaged", "newlywed", "married", "single"),
    ),
    QuestionTemplate(
        "q_housing_income",
        "housing",
        "household_income_range",
        "What is your household income range?",
        "single_select",
        True,
        30,
        90,
        options=("unknown", "under_50m", "50m_to_80m", "80m_to_120m", "over_120m"),
    ),
    QuestionTemplate(
        "q_housing_ownership",
        "housing",
        "housing_status",
        "Do you currently own a home?",
        "single_select",
        True,
        40,
        85,
        options=("no_home", "own_home", "unknown"),
    ),
    QuestionTemplate(
        "q_housing_lease_type",
        "housing",
        "lease_type",
        "What type of housing contract are you considering?",
        "single_select",
        True,
        50,
        70,
        options=("jeonse", "monthly_rent", "purchase", "unknown"),
    ),
    QuestionTemplate(
        "q_cash_region",
        "cash",
        "region",
        "Which region do you currently live in?",
        "single_select",
        True,
        10,
        100,
        options=("Seoul", "Daejeon", "Busan", "Jeonbuk", "National"),
    ),
    QuestionTemplate(
        "q_cash_marital_status",
        "cash",
        "marital_status",
        "What is your current marriage status?",
        "single_select",
        True,
        20,
        95,
        options=("engaged", "newlywed", "married", "single"),
    ),
    QuestionTemplate(
        "q_cash_marriage_registered",
        "cash",
        "marriage_registered",
        "Have you completed marriage registration?",
        "boolean",
        True,
        30,
        90,
        options=("true", "false"),
    ),
    QuestionTemplate(
        "q_cash_registration_date",
        "cash",
        "marriage_registration_date",
        "When was the marriage registration completed?",
        "date",
        True,
        40,
        80,
        parent_question_id="q_cash_marriage_registered",
        show_condition=ShowCondition("marriage_registered", True),
    ),
    QuestionTemplate(
        "q_childcare_region",
        "childcare",
        "region",
        "Which region do you currently live in?",
        "single_select",
        True,
        10,
        100,
        options=("National", "Sejong", "Seoul", "Gyeonggi"),
    ),
    QuestionTemplate(
        "q_childcare_pregnancy",
        "childcare",
        "pregnancy_status",
        "Are you preparing for pregnancy or currently pregnant?",
        "single_select",
        True,
        20,
        95,
        options=("preparing", "pregnant", "not_applicable", "unknown"),
    ),
    QuestionTemplate(
        "q_childcare_has_child",
        "childcare",
        "has_child",
        "Do you have a child?",
        "boolean",
        True,
        30,
        85,
        options=("true", "false"),
    ),
    QuestionTemplate(
        "q_childcare_child_age",
        "childcare",
        "child_age_months",
        "How old is the youngest child in months?",
        "number",
        True,
        40,
        75,
        parent_question_id="q_childcare_has_child",
        show_condition=ShowCondition("has_child", True),
    ),
    QuestionTemplate(
        "q_loan_region",
        "loan",
        "region",
        "Which region do you currently live in?",
        "single_select",
        True,
        10,
        100,
        options=("National", "Seoul", "Gyeonggi"),
    ),
    QuestionTemplate(
        "q_loan_marital_status",
        "loan",
        "marital_status",
        "What is your current marriage status?",
        "single_select",
        True,
        20,
        95,
        options=("engaged", "newlywed", "married", "single"),
    ),
    QuestionTemplate(
        "q_loan_income",
        "loan",
        "household_income_range",
        "What is your household income range?",
        "single_select",
        True,
        30,
        90,
        options=("unknown", "under_50m", "50m_to_80m", "80m_to_120m", "over_120m"),
    ),
    QuestionTemplate(
        "q_loan_credit_need",
        "loan",
        "loan_purpose",
        "What is the purpose of the loan support you need?",
        "single_select",
        True,
        40,
        80,
        options=("housing", "wedding", "settlement", "unknown"),
    ),
    QuestionTemplate(
        "q_education_region",
        "education",
        "region",
        "Which region do you currently live in?",
        "single_select",
        True,
        10,
        100,
        options=("National", "Seoul", "Gyeonggi"),
    ),
    QuestionTemplate(
        "q_education_topic",
        "education",
        "education_topic",
        "Which topic do you need help with?",
        "single_select",
        True,
        20,
        90,
        options=("housing_contract", "financial_counseling", "family_budget", "unknown"),
    ),
    QuestionTemplate(
        "q_education_marital_status",
        "education",
        "marital_status",
        "What is your current marriage status?",
        "single_select",
        True,
        30,
        80,
        options=("engaged", "newlywed", "married", "single"),
    ),
)




def questions_by_id(questions: tuple[QuestionTemplate, ...] = QUESTION_BANK) -> dict[str, QuestionTemplate]:
    return {question.question_id: question for question in questions}


def fact_to_question_ids(questions: tuple[QuestionTemplate, ...] = QUESTION_BANK) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for question in questions:
        mapping.setdefault(question.fact_key, set()).add(question.question_id)
    return mapping


def dependency_edges(questions: tuple[QuestionTemplate, ...] = QUESTION_BANK) -> dict[str, set[str]]:
    by_id = questions_by_id(questions)
    by_fact = fact_to_question_ids(questions)
    edges: dict[str, set[str]] = {question.question_id: set() for question in questions}
    for question in questions:
        parent_ids: set[str] = set()
        if question.parent_question_id is not None:
            if question.parent_question_id not in by_id:
                raise ValueError(f"Unknown parent question: {question.parent_question_id}")
            parent_ids.add(question.parent_question_id)
        if question.show_condition is not None:
            parent_ids.update(by_fact.get(question.show_condition.fact_key, set()))
        for parent_id in parent_ids:
            if by_id[parent_id].category_code == question.category_code:
                edges[parent_id].add(question.question_id)
    return edges


def validate_question_dag(questions: tuple[QuestionTemplate, ...] = QUESTION_BANK) -> None:
    edges = dependency_edges(questions)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(question_id: str) -> None:
        if question_id in visited:
            return
        if question_id in visiting:
            raise ValueError(f"Circular question dependency detected at {question_id}")
        visiting.add(question_id)
        for child_id in edges[question_id]:
            visit(child_id)
        visiting.remove(question_id)
        visited.add(question_id)

    for question_id in edges:
        visit(question_id)


def dependent_fact_keys(category_code: str, changed_fact_key: str) -> set[str]:
    by_fact = fact_to_question_ids()
    parent_ids = {
        question_id
        for question_id in by_fact.get(changed_fact_key, set())
        if questions_by_id()[question_id].category_code == category_code
    }
    edges = dependency_edges()
    dependent_question_ids: set[str] = set()
    pending = list(parent_ids)
    while pending:
        question_id = pending.pop()
        for child_id in edges.get(question_id, set()):
            if child_id in dependent_question_ids:
                continue
            dependent_question_ids.add(child_id)
            pending.append(child_id)
    by_id = questions_by_id()
    return {by_id[question_id].fact_key for question_id in dependent_question_ids}

def category_questions(category_code: str) -> list[QuestionTemplate]:
    return sorted(
        (question for question in QUESTION_BANK if question.category_code == category_code),
        key=lambda question: (question.priority, -question.discriminator_score, question.question_id),
    )


def show_condition_matches(question: QuestionTemplate, facts: dict[str, Any]) -> bool:
    if question.show_condition is None:
        return True
    return facts.get(question.show_condition.fact_key) == question.show_condition.equals


def visible_questions(category_code: str, facts: dict[str, Any]) -> list[QuestionTemplate]:
    return [question for question in category_questions(category_code) if show_condition_matches(question, facts)]


def unanswered_required_questions(category_code: str, facts: dict[str, Any]) -> list[QuestionTemplate]:
    return [
        question
        for question in visible_questions(category_code, facts)
        if question.required and question.fact_key not in facts
    ]


def next_questions(category_code: str, facts: dict[str, Any], limit: int = 1) -> list[QuestionTemplate]:
    return unanswered_required_questions(category_code, facts)[:limit]


def progress(category_code: str, facts: dict[str, Any]) -> tuple[int, int, bool]:
    questions = [question for question in visible_questions(category_code, facts) if question.required]
    answered = sum(1 for question in questions if question.fact_key in facts)
    total = len(questions)
    return answered, total, answered >= total


def question_for_fact(category_code: str, fact_key: str, facts: dict[str, Any]) -> QuestionTemplate | None:
    for question in visible_questions(category_code, facts):
        if question.fact_key == fact_key:
            return question
    return None


def supported_category(category_code: str) -> bool:
    return any(question.category_code == category_code for question in QUESTION_BANK)


validate_question_dag()