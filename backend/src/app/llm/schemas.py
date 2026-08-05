from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AIResultStatus(StrEnum):
    ANSWERED = "ANSWERED"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"


class AIConditionReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str = Field(alias="conditionId")
    label: str
    reason: str | None = None


class AICitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(alias="sourceId")
    title: str
    url: str
    policy_version_id: str = Field(alias="policyVersionId")
    excerpt: str | None = None


class AINextQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(alias="questionId")
    prompt: str
    fact_key: str = Field(alias="factKey")


class AIOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    answer: str
    result_status: AIResultStatus = Field(alias="resultStatus")
    matched_conditions: list[AIConditionReference] = Field(default_factory=list, alias="matchedConditions")
    missing_conditions: list[AIConditionReference] = Field(default_factory=list, alias="missingConditions")
    citations: list[AICitation] = Field(default_factory=list)
    next_question: AINextQuestion | None = Field(default=None, alias="nextQuestion")
