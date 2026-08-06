from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationEvidenceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    satisfied: list[dict[str, Any]] = Field(default_factory=list)
    unsatisfied: list[dict[str, Any]] = Field(default_factory=list)
    needs_confirmation: list[dict[str, Any]] = Field(default_factory=list, alias="needsConfirmation")
    official_confirmation_required: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="officialConfirmationRequired",
    )


class PolicyEvaluationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    policy_id: str = Field(alias="policyId")
    eligibility_status: str = Field(alias="eligibilityStatus")
    evaluation_state: str = Field(alias="evaluationState")
    recommendation_score: int = Field(alias="recommendationScore")
    evidence: EvaluationEvidenceResponse
    evaluated_at: str = Field(alias="evaluatedAt")
    updated_at: str = Field(alias="updatedAt")


class CreateEvaluationsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    items: list[PolicyEvaluationResponse]