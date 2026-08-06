from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SelectCategoryRequest(BaseModel):
    category_code: str = Field(alias="categoryCode", min_length=1, max_length=50)


class SelectCategoryResponse(BaseModel):
    category_code: str = Field(alias="categoryCode")
    status: str = "category_selected"


class QuestionOptionResponse(BaseModel):
    label: str
    value: str


class ShowConditionResponse(BaseModel):
    fact_key: str = Field(alias="factKey")
    equals: Any


class QuestionResponse(BaseModel):
    question_id: str = Field(alias="questionId")
    fact_key: str = Field(alias="factKey")
    prompt: str
    answer_type: str = Field(alias="answerType")
    required: bool
    priority: int
    parent_question_id: str | None = Field(default=None, alias="parentQuestionId")
    show_condition: ShowConditionResponse | None = Field(default=None, alias="showCondition")
    options: list[QuestionOptionResponse] = []
    is_conflict_resolution: bool = Field(default=False, alias="isConflictResolution")
    conflict_reason: str | None = Field(default=None, alias="conflictReason")


class NextQuestionsResponse(BaseModel):
    category_code: str | None = Field(alias="categoryCode")
    items: list[QuestionResponse]
    complete: bool


class AnswerInput(BaseModel):
    question_id: str = Field(alias="questionId", min_length=1, max_length=80)
    fact_key: str = Field(alias="factKey", min_length=1, max_length=80)
    value: Any
    confirmed: bool = True


class SubmitAnswersRequest(BaseModel):
    answers: list[AnswerInput] = Field(min_length=1, max_length=50)


class AnswerConflictResponse(BaseModel):
    fact_key: str = Field(alias="factKey")
    existing_value: Any = Field(alias="existingValue")
    submitted_value: Any = Field(alias="submittedValue")
    question: QuestionResponse | None = None


class SubmitAnswersResponse(BaseModel):
    status: str
    stored: list[str]
    conflicts: list[AnswerConflictResponse]
    next_questions: list[QuestionResponse] = Field(alias="nextQuestions")


class QuestionProgressResponse(BaseModel):
    category_code: str | None = Field(alias="categoryCode")
    answered_required: int = Field(alias="answeredRequired")
    total_required: int = Field(alias="totalRequired")
    complete: bool
