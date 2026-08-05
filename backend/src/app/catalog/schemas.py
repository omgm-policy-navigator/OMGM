from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str | None = None


class PolicySummaryResponse(BaseModel):
    policy_id: str = Field(alias="policyId")
    category_code: str = Field(alias="categoryCode")
    title: str
    agency: str
    region: str
    application_period: str = Field(alias="applicationPeriod")
    status: str
    official_source_url: str = Field(alias="officialSourceUrl")
    reviewed_at: date = Field(alias="reviewedAt")


class PolicySourceResponse(BaseModel):
    label: str
    url: str
    reviewed_at: date = Field(alias="reviewedAt")


class PolicyDetailResponse(BaseModel):
    policy_id: str = Field(alias="policyId")
    category_code: str = Field(alias="categoryCode")
    title: str
    agency: str
    region: str
    summary: str
    application_period: str = Field(alias="applicationPeriod")
    support_type: str = Field(alias="supportType")
    status: str
    source: PolicySourceResponse


class PolicyDocumentResponse(BaseModel):
    document_id: str = Field(alias="documentId")
    policy_id: str = Field(alias="policyId")
    title: str
    url: str
    document_type: str = Field(alias="documentType")
    official_source: str = Field(alias="officialSource")
    reviewed_at: date = Field(alias="reviewedAt")
    collected_at: datetime = Field(alias="collectedAt")
    document_hash: str = Field(alias="documentHash")