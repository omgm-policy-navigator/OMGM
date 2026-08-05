from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AIResultStatus(StrEnum):
    ANSWERED = "ANSWERED"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"


class AIConditionReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str = Field(alias="conditionId", min_length=1)
    label: str = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=500)


class AICitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(alias="sourceId", min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    policy_version_id: str = Field(alias="policyVersionId", min_length=1)
    evidence_id: str = Field(alias="evidenceId", min_length=1)
    excerpt: str | None = Field(default=None, max_length=500)

    @field_validator("url")
    @classmethod
    def validate_public_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("citation url must be an absolute http or https URL")
        if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("citation url must not point to a local address")
        return value


class AINextQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(alias="questionId", min_length=1)
    prompt: str = Field(min_length=1, max_length=500)
    fact_key: str = Field(alias="factKey", min_length=1)


class AIOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    answer: str = Field(min_length=1, max_length=2000)
    result_status: AIResultStatus = Field(alias="resultStatus")
    matched_conditions: list[AIConditionReference] = Field(default_factory=list, alias="matchedConditions")
    missing_conditions: list[AIConditionReference] = Field(default_factory=list, alias="missingConditions")
    citations: list[AICitation] = Field(default_factory=list)
    next_question: AINextQuestion | None = Field(default=None, alias="nextQuestion")

    @model_validator(mode="after")
    def validate_status_contract(self) -> "AIOutput":
        matched_ids = {condition.condition_id for condition in self.matched_conditions}
        missing_ids = {condition.condition_id for condition in self.missing_conditions}
        overlapping_ids = matched_ids.intersection(missing_ids)
        if overlapping_ids:
            raise ValueError("matchedConditions and missingConditions must not contain the same conditionId")

        evidence_ids = [citation.evidence_id for citation in self.citations]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("citations must not contain duplicate evidenceId values")

        if self.result_status == AIResultStatus.ANSWERED:
            if not self.citations:
                raise ValueError("ANSWERED requires at least one citation")
            if self.missing_conditions:
                raise ValueError("ANSWERED must not include missingConditions")
            if self.next_question is not None:
                raise ValueError("ANSWERED must not include nextQuestion")

        if self.result_status == AIResultStatus.NEEDS_CONFIRMATION and not self.missing_conditions:
            raise ValueError("NEEDS_CONFIRMATION requires missingConditions")

        if self.result_status == AIResultStatus.INSUFFICIENT_EVIDENCE and self.citations:
            raise ValueError("INSUFFICIENT_EVIDENCE must not include citations")

        if self.result_status in {AIResultStatus.LLM_UNAVAILABLE, AIResultStatus.SAFETY_BLOCKED}:
            if self.matched_conditions or self.missing_conditions or self.citations or self.next_question is not None:
                raise ValueError(f"{self.result_status} must not include derived evidence fields")

        return self
