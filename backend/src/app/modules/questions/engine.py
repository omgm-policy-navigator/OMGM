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
