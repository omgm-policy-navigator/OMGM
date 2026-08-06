from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AIResponseStatus(StrEnum):
    GENERATED = "GENERATED"
    FALLBACK = "FALLBACK"
    OFFICIAL_CONFIRMATION_REQUIRED = "OFFICIAL_CONFIRMATION_REQUIRED"


class CitationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(alias="sourceId")
    policy_id: str = Field(alias="policyId")
    title: str
    url: str
    source_label: str = Field(alias="sourceLabel")
    evidence_id: str = Field(alias="evidenceId")
    excerpt: str | None = None
    source_location: str | None = Field(default=None, alias="sourceLocation")
    similarity: float | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(min_length=1, max_length=1000)
    policy_id: str | None = Field(default=None, alias="policyId", max_length=80)


class PolicyExplainRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str | None = Field(default=None, min_length=1, max_length=1000)


class AIExplanationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    policy_id: str | None = Field(alias="policyId")
    eligibility_status: str = Field(alias="eligibilityStatus")
    evaluation_state: str | None = Field(default=None, alias="evaluationState")
    ai_status: AIResponseStatus = Field(alias="aiStatus")
    answer: str
    citations: list[CitationResponse]


class ChatStreamEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    text: str | None = None
