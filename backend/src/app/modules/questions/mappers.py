from __future__ import annotations

from typing import Any

from app.modules.questions.engine import QuestionTemplate, ShowCondition
from app.modules.questions.schemas import QuestionOptionResponse, QuestionResponse, ShowConditionResponse
from app.modules.sessions.models import UserFact


def facts_to_dict(facts: list[UserFact]) -> dict[str, Any]:
    return {fact.condition_key: fact.value for fact in facts}


def question_to_response(question: QuestionTemplate) -> QuestionResponse:
    show_condition = None
    if question.show_condition is not None:
        show_condition = show_condition_to_response(question.show_condition)
    return QuestionResponse(
        questionId=question.question_id,
        factKey=question.fact_key,
        prompt=question.prompt,
        answerType=question.answer_type,
        required=question.required,
        priority=question.priority,
        parentQuestionId=question.parent_question_id,
        showCondition=show_condition,
        options=[QuestionOptionResponse(label=option, value=option) for option in question.options],
    )


def show_condition_to_response(show_condition: ShowCondition) -> ShowConditionResponse:
    return ShowConditionResponse(factKey=show_condition.fact_key, equals=show_condition.equals)