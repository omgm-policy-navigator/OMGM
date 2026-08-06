from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from http import HTTPStatus

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppConfig
from app.core.errors import AppError
from app.db.session import get_db
from app.llm import LLMProvider, create_available_llm_provider
from app.modules.ai.repository import (
    find_policy_evidence_bundle_for_message,
    get_policy_evidence_bundle,
    get_top_session_policy_evidence_bundle,
)
from app.modules.ai.schemas import (
    AIExplanationResponse,
    ChatRequest,
    ChatStreamEvent,
    CitationResponse,
    PolicyExplainRequest,
)
from app.modules.ai.service import ExplanationContext, explain_with_ai
from app.modules.rag.embedding import EmbeddingProvider, OllamaEmbeddingProvider
from app.modules.rag.repository import SqlAlchemyRagSearchRepository
from app.modules.rag.search import Citation, search_policy_evidence
from app.modules.sessions.security import validate_unsafe_origin
from app.modules.sessions.service import require_session

RAG_TIMEOUT_SECONDS = 3
RAG_MINIMUM_SIMILARITY = 0.75
RAG_TOP_K = 3

router = APIRouter(prefix="/api", tags=["ai"])


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


DB_DEPENDENCY = Depends(get_db)
CONFIG_DEPENDENCY = Depends(get_config)


def allowed_origins(config: AppConfig) -> list[str]:
    return [origin.strip() for origin in config.cors_allowed_origins.split(",")]


async def get_embedding_provider(request: Request) -> EmbeddingProvider:
    provider = getattr(request.app.state, "embedding_provider", None)
    if provider is not None:
        return provider
    config = request.app.state.config
    provider = OllamaEmbeddingProvider(
        base_url=config.ollama_base_url,
        model=config.ollama_embedding_model,
        timeout_seconds=config.llm_timeout_seconds,
    )
    request.app.state.embedding_provider = provider
    return provider


async def get_llm_provider(request: Request) -> LLMProvider | None:
    provider = getattr(request.app.state, "llm_provider", None)
    if provider is not None:
        return provider
    try:
        provider = await create_available_llm_provider(request.app.state.config)
    except Exception:
        return None
    request.app.state.llm_provider = provider
    return provider


async def retrieve_rag_citations(
    db: AsyncSession,
    request: Request,
    *,
    policy_id: str,
    question: str,
) -> tuple[CitationResponse, ...]:
    try:
        result = await asyncio.wait_for(
            search_policy_evidence(
                policy_id=policy_id,
                question=question,
                provider=await get_embedding_provider(request),
                repository=SqlAlchemyRagSearchRepository(db),
                top_k=RAG_TOP_K,
                minimum_similarity=RAG_MINIMUM_SIMILARITY,
            ),
            timeout=RAG_TIMEOUT_SECONDS,
        )
    except Exception:
        return ()
    return tuple(citation_response(policy_id, citation) for citation in result.citations)


def citation_response(policy_id: str, citation: Citation) -> CitationResponse:
    return CitationResponse(
        sourceId=citation.source_id,
        policyId=policy_id,
        title=citation.title,
        url=citation.url,
        sourceLabel="OFFICIAL",
        evidenceId=citation.evidence_id,
        excerpt=citation.excerpt,
        sourceLocation=citation.source_location,
        similarity=citation.similarity,
    )


def rag_query_for_bundle(bundle) -> str:
    policy = bundle.policy
    evidence = bundle.evaluation.evidence if bundle.evaluation is not None else {}
    condition_keys = sorted(
        {
            item.get("factKey")
            for group_name in (
                "satisfied",
                "unsatisfied",
                "needsConfirmation",
                "officialConfirmationRequired",
            )
            for item in evidence.get(group_name, [])
            if isinstance(item, dict) and isinstance(item.get("factKey"), str)
        }
    )
    keywords = [policy.title, policy.category_code, policy.support_type, *condition_keys]
    return " ".join(str(keyword) for keyword in keywords if str(keyword).strip())


TOP_POLICY_FALLBACK_PATTERNS = (
    "가장 적절",
    "추천",
    "맞는 정책",
    "가능한 정책",
    "신청 가능",
    "나한테 맞",
    "우리에게 맞",
    "뭐가 좋아",
    "어떤 정책",
    "which policy",
    "recommend",
    "best policy",
)


def should_use_top_policy_fallback(message: str) -> bool:
    normalized = message.casefold()
    return any(pattern in normalized for pattern in TOP_POLICY_FALLBACK_PATTERNS)


async def build_context_for_policy(
    db: AsyncSession,
    request: Request,
    *,
    session_id: int,
    policy_id: str,
    user_message: str | None,
) -> ExplanationContext:
    bundle = await get_policy_evidence_bundle(db, session_id=session_id, policy_id=policy_id)
    if bundle is None:
        raise AppError("POLICY_NOT_FOUND", "Requested policy does not exist.", HTTPStatus.NOT_FOUND)
    question = rag_query_for_bundle(bundle)
    return ExplanationContext(
        policy=bundle.policy,
        evaluation=bundle.evaluation,
        documents=bundle.documents,
        retrieved_citations=await retrieve_rag_citations(db, request, policy_id=policy_id, question=question),
        user_message=user_message,
    )


async def build_context_for_top_policy(
    db: AsyncSession,
    request: Request,
    *,
    session_id: int,
    user_message: str,
    category_code: str | None = None,
) -> ExplanationContext:
    bundle = await find_policy_evidence_bundle_for_message(
        db,
        session_id=session_id,
        category_code=category_code,
        message=user_message,
    )
    if bundle is None:
        if not should_use_top_policy_fallback(user_message):
            return ExplanationContext(policy=None, evaluation=None, documents=(), user_message=user_message)
        bundle = await get_top_session_policy_evidence_bundle(db, session_id=session_id)
    if bundle is None:
        return ExplanationContext(policy=None, evaluation=None, documents=(), user_message=user_message)
    return ExplanationContext(
        policy=bundle.policy,
        evaluation=bundle.evaluation,
        documents=bundle.documents,
        retrieved_citations=await retrieve_rag_citations(
            db,
            request,
            policy_id=bundle.policy.id,
            question=rag_query_for_bundle(bundle),
        ),
        user_message=user_message,
    )


@router.post("/chat", response_model=AIExplanationResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> AIExplanationResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    if payload.policy_id is not None:
        context = await build_context_for_policy(
            db,
            request,
            session_id=session.id,
            policy_id=payload.policy_id,
            user_message=payload.message,
        )
    else:
        context = await build_context_for_top_policy(
            db,
            request,
            session_id=session.id,
            user_message=payload.message,
            category_code=session.selected_category_code,
        )
    response = await explain_with_ai(context, await get_llm_provider(request))
    await db.commit()
    return response


@router.post("/policies/{policy_id}/explain", response_model=AIExplanationResponse)
async def explain_policy(
    policy_id: str,
    payload: PolicyExplainRequest,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> AIExplanationResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    context = await build_context_for_policy(
        db,
        request,
        session_id=session.id,
        policy_id=policy_id,
        user_message=payload.question,
    )
    response = await explain_with_ai(context, await get_llm_provider(request))
    await db.commit()
    return response


@router.get("/chat/stream")
async def chat_stream(
    request: Request,
    message: str,
    policy_id: str | None = None,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> StreamingResponse:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    if policy_id is not None:
        context = await build_context_for_policy(
            db,
            request,
            session_id=session.id,
            policy_id=policy_id,
            user_message=message,
        )
    else:
        context = await build_context_for_top_policy(
            db,
            request,
            session_id=session.id,
            user_message=message,
            category_code=session.selected_category_code,
        )
    response = await explain_with_ai(context, await get_llm_provider(request))
    await db.commit()

    async def events() -> AsyncIterator[str]:
        yield sse("status", ChatStreamEvent(status="started"))
        yield sse("message", ChatStreamEvent(status="streaming", text=response.answer))
        yield sse("done", ChatStreamEvent(status="done"))

    return StreamingResponse(events(), media_type="text/event-stream")


def sse(event: str, payload: ChatStreamEvent) -> str:
    return f"event: {event}\ndata: {json.dumps(payload.model_dump(by_alias=True), ensure_ascii=False)}\n\n"
