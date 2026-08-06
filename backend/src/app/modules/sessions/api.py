from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppConfig
from app.core.errors import AppError
from app.db.session import get_db
from app.modules.eligibility.repository import (
    delete_session_evaluations_for_category,
    get_session_policy_evaluation,
    list_active_policies_for_category,
    list_session_evaluations,
    mark_session_evaluations_stale,
    upsert_policy_evaluation,
)
from app.modules.eligibility.schemas import CreateEvaluationsResponse, PolicyEvaluationResponse
from app.modules.eligibility.service import evaluate_policy, evaluation_to_response, evidence_from_result
from app.modules.graph.projection import CENTERED_GRAPH_MAX_DEPTH, build_session_graph
from app.modules.graph.repository import (
    list_centered_graph_policy_ids,
    list_graph_categories,
    list_graph_evaluations,
    list_graph_policies,
    list_graph_relations,
)
from app.modules.graph.schemas import SessionGraphResponse
from app.modules.questions.engine import (
    category_questions,
    dependent_fact_keys,
    next_questions,
    progress,
    question_for_fact,
    supported_category,
)
from app.modules.questions.mappers import question_to_response
from app.modules.questions.schemas import (
    AnswerConflictResponse,
    NextQuestionsResponse,
    QuestionProgressResponse,
    QuestionResponse,
    SelectCategoryRequest,
    SelectCategoryResponse,
    SubmitAnswersRequest,
    SubmitAnswersResponse,
)
from app.modules.sessions.schemas import (
    CreateSessionResponse,
    ResetCategorySessionRequest,
    ResetCategorySessionResponse,
    SessionResponse,
    UpsertUserFactRequest,
    UserFactResponse,
)
from app.modules.sessions.security import validate_unsafe_origin
from app.modules.sessions.service import (
    cleanup_expired_sessions,
    create_or_get_session,
    delete_current_session,
    delete_session_facts_by_keys,
    list_session_facts,
    require_session,
    upsert_session_fact,
)

router = APIRouter(prefix="/api/v1/session", tags=["session"])

FORBIDDEN_SESSION_INPUTS = {"session_id", "sessionId", "anonymous_session", "x-session-id"}
FACT_SCOPE_SEPARATOR = ":"


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


DB_DEPENDENCY = Depends(get_db)
CONFIG_DEPENDENCY = Depends(get_config)


def cookie_secure(config: AppConfig) -> bool:
    return config.app_env.lower() != "local"


def allowed_origins(config: AppConfig) -> list[str]:
    return [origin.strip() for origin in config.cors_allowed_origins.split(",")]


def set_session_cookie(response: Response, config: AppConfig, token: str) -> None:
    response.set_cookie(
        key=config.anonymous_session_cookie_name,
        value=token,
        max_age=config.anonymous_session_absolute_ttl_minutes * 60,
        httponly=True,
        secure=cookie_secure(config),
        samesite=config.anonymous_session_cookie_samesite,
        path="/",
    )


def clear_session_cookie(response: Response, config: AppConfig) -> None:
    response.delete_cookie(
        key=config.anonymous_session_cookie_name,
        httponly=True,
        secure=cookie_secure(config),
        samesite=config.anonymous_session_cookie_samesite,
        path="/",
    )


def reject_session_identifier() -> None:
    raise AppError(
        "VALIDATION_ERROR",
        "Session identifiers must be sent only by cookie.",
        HTTPStatus.UNPROCESSABLE_ENTITY,
    )


async def reject_client_session_injection(request: Request) -> None:
    if any(name in request.headers for name in ("x-session-id", "x-anonymous-session")):
        reject_session_identifier()
    if not request.headers.get("content-type", "").startswith("application/json"):
        return
    payload = await request.json()
    if isinstance(payload, dict) and FORBIDDEN_SESSION_INPUTS.intersection(payload):
        reject_session_identifier()


def require_category_code(category_code: str | None) -> str:
    if category_code is None:
        raise AppError(
            "VALIDATION_ERROR",
            "A session category must be selected first.",
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    return category_code


def validate_category_code(category_code: str) -> str:
    normalized = category_code.strip().lower()
    if not supported_category(normalized):
        raise AppError(
            "VALIDATION_ERROR",
            "Category is not supported by the question engine.",
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    return normalized


def scoped_fact_key(category_code: str, fact_key: str) -> str:
    return f"{category_code}{FACT_SCOPE_SEPARATOR}{fact_key}"


def scoped_fact_keys(category_code: str, fact_keys: set[str]) -> set[str]:
    return {scoped_fact_key(category_code, fact_key) for fact_key in fact_keys}


def legacy_and_scoped_fact_keys(category_code: str, fact_keys: set[str]) -> set[str]:
    return fact_keys | scoped_fact_keys(category_code, fact_keys)


def facts_to_category_dict(facts: list[Any], category_code: str) -> dict[str, Any]:
    prefix = f"{category_code}{FACT_SCOPE_SEPARATOR}"
    scoped: dict[str, Any] = {}
    for fact in facts:
        condition_key = str(fact.condition_key)
        if condition_key.startswith(prefix):
            scoped[condition_key.removeprefix(prefix)] = fact.value
    return scoped


def conflict_question_response(question: QuestionResponse, fact_key: str) -> QuestionResponse:
    question.is_conflict_resolution = True
    question.conflict_reason = f"Submitted answer conflicts with the existing confirmed fact for {fact_key}."
    return question


def detect_answer_conflicts(
    category_code: str,
    existing_facts: dict[str, Any],
    submitted_facts: dict[str, Any],
) -> list[AnswerConflictResponse]:
    conflicts: list[AnswerConflictResponse] = []
    combined = dict(existing_facts)
    combined.update(submitted_facts)
    for fact_key, submitted_value in submitted_facts.items():
        if fact_key not in existing_facts or existing_facts[fact_key] == submitted_value:
            continue
        if dependent_fact_keys(category_code, fact_key):
            continue
        question = question_for_fact(category_code, fact_key, combined)
        question_response = question_to_response(question) if question else None
        conflicts.append(
            AnswerConflictResponse(
                factKey=fact_key,
                existingValue=existing_facts[fact_key],
                submittedValue=submitted_value,
                question=conflict_question_response(question_response, fact_key) if question_response else None,
            )
        )
    return conflicts


@router.post("", response_model=CreateSessionResponse, status_code=HTTPStatus.CREATED)
async def create_session(
    request: Request,
    response: Response,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> CreateSessionResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    await reject_client_session_injection(request)
    await cleanup_expired_sessions(db)
    result = await create_or_get_session(
        db,
        config,
        request.cookies.get(config.anonymous_session_cookie_name),
    )
    await db.commit()
    if result.token is not None:
        set_session_cookie(response, config, result.token)
    if not result.created:
        response.status_code = HTTPStatus.OK
        return CreateSessionResponse(status="session_active")
    return CreateSessionResponse(status="session_created")


@router.get("", response_model=SessionResponse)
async def get_session(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> SessionResponse:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    await db.commit()
    return SessionResponse(expiresAt=session.expires_at, idleExpiresAt=session.idle_expires_at)


@router.delete("", status_code=HTTPStatus.NO_CONTENT)
async def delete_session(
    request: Request,
    response: Response,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> Response:
    validate_unsafe_origin(request, allowed_origins(config))
    await delete_current_session(db, request.cookies.get(config.anonymous_session_cookie_name))
    await db.commit()
    clear_session_cookie(response, config)
    response.status_code = HTTPStatus.NO_CONTENT
    return response


@router.post("/category", response_model=SelectCategoryResponse)
async def select_category(
    payload: SelectCategoryRequest,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> SelectCategoryResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    category_code = validate_category_code(payload.category_code)
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    session.selected_category_code = category_code
    await db.commit()
    return SelectCategoryResponse(categoryCode=category_code)


@router.post("/category/reset", response_model=ResetCategorySessionResponse)
async def reset_category_session(
    payload: ResetCategorySessionRequest,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> ResetCategorySessionResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    category_code = validate_category_code(payload.category_code)
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    session.selected_category_code = category_code
    fact_keys = {question.fact_key for question in category_questions(category_code)}
    deleted_facts = await delete_session_facts_by_keys(
        db,
        session,
        legacy_and_scoped_fact_keys(category_code, fact_keys),
    )
    deleted_evaluations = await delete_session_evaluations_for_category(db, session.id, category_code)
    await db.commit()
    return ResetCategorySessionResponse(
        categoryCode=category_code,
        deletedFacts=deleted_facts,
        deletedEvaluations=deleted_evaluations,
    )


@router.get("/facts", response_model=list[UserFactResponse])
async def get_facts(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> list[UserFactResponse]:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    facts = await list_session_facts(db, session)
    await db.commit()
    return [
        UserFactResponse(
            conditionKey=fact.condition_key,
            value=fact.value,
            source=fact.source,
            confirmed=fact.confirmed,
            updatedAt=fact.updated_at,
        )
        for fact in facts
    ]


@router.put("/facts/{condition_key}", response_model=UserFactResponse)
async def put_fact(
    condition_key: str,
    payload: UpsertUserFactRequest,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> UserFactResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    fact = await upsert_session_fact(
        db,
        session,
        condition_key,
        payload.value,
        payload.source,
        payload.confirmed,
        payload.note,
    )
    await mark_session_evaluations_stale(db, session.id)
    await db.commit()
    return UserFactResponse(
        conditionKey=fact.condition_key,
        value=fact.value,
        source=fact.source,
        confirmed=fact.confirmed,
        updatedAt=fact.updated_at,
    )


@router.get("/questions/next", response_model=NextQuestionsResponse)
async def get_next_questions(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> NextQuestionsResponse:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    category_code = require_category_code(session.selected_category_code)
    facts = facts_to_category_dict(await list_session_facts(db, session), category_code)
    _answered, _total, complete = progress(category_code, facts)
    await db.commit()
    return NextQuestionsResponse(
        categoryCode=category_code,
        items=[question_to_response(question) for question in next_questions(category_code, facts)],
        complete=complete,
    )


@router.post("/answers", response_model=SubmitAnswersResponse)
async def submit_answers(
    payload: SubmitAnswersRequest,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> SubmitAnswersResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    category_code = require_category_code(session.selected_category_code)
    current_facts = await list_session_facts(db, session)
    existing_facts = facts_to_category_dict(current_facts, category_code)
    submitted_facts = {answer.fact_key: answer.value for answer in payload.answers}
    conflicts = detect_answer_conflicts(category_code, existing_facts, submitted_facts)
    if conflicts:
        await db.commit()
        return SubmitAnswersResponse(status="conflicted", stored=[], conflicts=conflicts, nextQuestions=[])

    stored: list[str] = []
    invalidated: set[str] = set()
    for answer in payload.answers:
        changed = answer.fact_key in existing_facts and existing_facts[answer.fact_key] != answer.value
        stale_fact_keys = (
            scoped_fact_keys(category_code, dependent_fact_keys(category_code, answer.fact_key))
            if changed
            else set()
        )
        await upsert_session_fact(
            db,
            session,
            scoped_fact_key(category_code, answer.fact_key),
            answer.value,
            f"question_engine:{category_code}",
            answer.confirmed,
            None,
        )
        await delete_session_facts_by_keys(db, session, stale_fact_keys)
        invalidated.update(stale_fact_keys)
        stored.append(answer.fact_key)
    merged_facts = dict(existing_facts)
    merged_facts.update(submitted_facts)
    for fact_key in invalidated:
        merged_facts.pop(fact_key, None)
    follow_ups = [question_to_response(question) for question in next_questions(category_code, merged_facts)]
    if stored:
        await mark_session_evaluations_stale(db, session.id)
    await db.commit()
    return SubmitAnswersResponse(status="stored", stored=stored, conflicts=[], nextQuestions=follow_ups)


@router.get("/questions/progress", response_model=QuestionProgressResponse)
async def get_question_progress(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> QuestionProgressResponse:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    category_code = require_category_code(session.selected_category_code)
    facts = facts_to_category_dict(await list_session_facts(db, session), category_code)
    answered, total, complete = progress(category_code, facts)
    await db.commit()
    return QuestionProgressResponse(
        categoryCode=category_code,
        answeredRequired=answered,
        totalRequired=total,
        complete=complete,
    )



@router.get("/graph", response_model=SessionGraphResponse)
async def get_session_graph(
    request: Request,
    category: str | None = None,
    policy_id: str | None = None,
    max_nodes: int | None = None,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> SessionGraphResponse:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    selected_category = validate_category_code(category) if category is not None else session.selected_category_code
    facts = (
        facts_to_category_dict(await list_session_facts(db, session), selected_category)
        if selected_category is not None
        else {}
    )
    centered_policy_ids = None
    if policy_id is not None:
        centered_policy_ids = await list_centered_graph_policy_ids(
            db,
            policy_id,
            max_depth=CENTERED_GRAPH_MAX_DEPTH,
            category_code=selected_category,
        )
    categories = await list_graph_categories(db, selected_category)
    policies = await list_graph_policies(
        db,
        selected_category if policy_id is None else None,
        centered_policy_ids,
    )
    visible_policy_ids = {policy.id for policy in policies}
    evaluations = await list_graph_evaluations(db, session.id, visible_policy_ids) if facts else []
    relations = await list_graph_relations(db, visible_policy_ids)
    graph = build_session_graph(
        facts=facts,
        categories=categories,
        policies=policies,
        evaluations=evaluations,
        relations=relations,
        selected_category_code=selected_category,
        selected_policy_id=policy_id,
        max_nodes=max_nodes,
    )
    await db.commit()
    return graph


@router.post("/evaluations", response_model=CreateEvaluationsResponse)
async def create_session_evaluations(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> CreateEvaluationsResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    category_code = require_category_code(session.selected_category_code)
    facts = facts_to_category_dict(await list_session_facts(db, session), category_code)
    policies = await list_active_policies_for_category(db, category_code)
    stored = []
    for policy in policies:
        result = evaluate_policy(policy, facts)
        evaluation = await upsert_policy_evaluation(
            db,
            session_id=session.id,
            policy_id=policy.id,
            eligibility_status=result.eligibility_status,
            evaluation_state=result.evaluation_state,
            recommendation_score=result.recommendation_score,
            evidence=evidence_from_result(result),
            fact_snapshot=facts,
        )
        stored.append(evaluation)
    stored.sort(key=lambda item: (-item.recommendation_score, item.policy_id))
    await db.commit()
    return CreateEvaluationsResponse(status="evaluated", items=[evaluation_to_response(item) for item in stored])


@router.get("/evaluations", response_model=list[PolicyEvaluationResponse])
async def get_session_evaluations(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> list[PolicyEvaluationResponse]:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    evaluations = await list_session_evaluations(db, session.id)
    await db.commit()
    return [evaluation_to_response(evaluation) for evaluation in evaluations]


@router.get("/evaluations/{policy_id}", response_model=PolicyEvaluationResponse)
async def get_session_policy_evaluation_result(
    policy_id: str,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> PolicyEvaluationResponse:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    evaluation = await get_session_policy_evaluation(db, session.id, policy_id)
    await db.commit()
    if evaluation is None:
        raise AppError("EVALUATION_NOT_FOUND", "Requested evaluation does not exist.", HTTPStatus.NOT_FOUND)
    return evaluation_to_response(evaluation)
