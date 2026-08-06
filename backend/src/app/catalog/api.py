from __future__ import annotations

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.repository import (
    get_approved_policy,
    list_categories,
    list_policies_by_category,
    list_policy_documents,
)
from app.catalog.schemas import CategoryResponse, PolicyDetailResponse, PolicyDocumentResponse, PolicySummaryResponse
from app.core.errors import AppError
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["policy-catalog"])
SessionDependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(db: SessionDependency) -> list[CategoryResponse]:
    return await list_categories(db)


@router.get("/categories/{code}/policies", response_model=list[PolicySummaryResponse])
async def get_category_policies(code: str, db: SessionDependency) -> list[PolicySummaryResponse]:
    return await list_policies_by_category(db, code)


@router.get("/policies/{policy_id}", response_model=PolicyDetailResponse)
async def get_policy(policy_id: str, db: SessionDependency) -> PolicyDetailResponse:
    policy = await get_approved_policy(db, policy_id)
    if policy is None:
        raise AppError("POLICY_NOT_FOUND", "Requested policy was not found.", HTTPStatus.NOT_FOUND)
    return policy


@router.get("/policies/{policy_id}/documents", response_model=list[PolicyDocumentResponse])
async def get_policy_documents(policy_id: str, db: SessionDependency) -> list[PolicyDocumentResponse]:
    documents = await list_policy_documents(db, policy_id)
    if documents is None:
        raise AppError("POLICY_NOT_FOUND", "Requested policy was not found.", HTTPStatus.NOT_FOUND)
    return documents