# 나만 결혼해?

결혼을 준비하거나 신혼생활을 시작한 사용자가 자신에게 맞는 결혼·신혼부부 지원정책을 찾고, 왜 신청 가능하거나 확인이 필요한지 정책 원문 근거와 함께 이해하도록 돕는 서비스입니다.

이 프로젝트는 단순 추천 앱이 아닙니다. 정책 원문, 구조화된 조건, 사용자 사실 정보를 분리해 관리하고, 최종 자격 상태는 LLM의 자유 추론이 아니라 Rule Engine의 결정론적 비교로 계산합니다. 정보가 부족하면 탈락시키지 않고 `NEEDS_CONFIRMATION`으로 처리하며, 정책 기준이 바뀌면 기존 판정을 `STALE`로 다룹니다.

## 저장소 구조

- `frontend/`: React Web UI.
- `backend/`: FastAPI 모듈러 모놀리스 API.
- `backend/data/policy-seed/`: 검수된 정책·질문·Rule·관계·RAG 문서 CSV 기준본.
- `infra/`: PostgreSQL, pgvector, Ollama 로컬 인프라.
- `docs/`: 제품, 아키텍처, 도메인, 데이터, RAG, 보안 문서.
- `scripts/`: 검증 보조 스크립트.
- `sample-data/`: 비민감 샘플 입력.

## 아키텍처

```text
React Web
  -> REST API / SSE
FastAPI Modular Monolith
  -> Conversation / Question / Rule Engine / RAG / Graph Projection
  -> PostgreSQL + pgvector
  -> Ollama

Reviewed Policy CSV Seed
  -> FastAPI policy catalog / Rule input / RAG document input
```

PostgreSQL은 정책, 질문, 사용자 사실, 규칙, 판정, 관계 같은 정형 데이터를 관리합니다. pgvector는 정책 원문 청크와 임베딩 검색을 PostgreSQL 안에서 처리합니다. Ollama는 질문 이해, 검색 질의 보정, 조건 후보 추출 보조, 설명 생성을 담당하지만 최종 판정을 결정하지 않습니다.

## 빠른 시작

```bash
cp .env.example .env
# edit .env and replace local placeholder passwords with a non-shared local value
make dev
```

Health Check:

```bash
make health
```

`.env.example`의 비밀번호와 연결 문자열은 로컬 placeholder입니다. `make dev`는 `.env`가 없거나 placeholder가 그대로 남아 있으면 실행을 중단합니다. `VITE_*` 환경변수는 브라우저에 노출되므로 Secret을 넣지 않습니다.

## 주요 명령

```bash
make help
make dev
make dev-logs
make dev-down
make env-check
make setup
make test
make verify
make compose-config
make docker-up
make docker-infra-up
make docker-ps
make docker-logs
make docker-down
```

개별 실행 세부 내용은 [Backend](backend/README.md), [Frontend](frontend/README.md), [Infra](infra/README.md)를 확인합니다.

## 핵심 문서

- [제품 개요](docs/product/product-overview.md)
- [사용자 시나리오](docs/product/user-scenarios.md)
- [MVP 범위](docs/product/mvp-scope.md)
- [시스템 개요](docs/architecture/system-overview.md)
- [백엔드 아키텍처](docs/architecture/backend.md)
- [API 계약](docs/architecture/api-contracts.md)
- [AI 계약](docs/architecture/ai-contracts.md)
- [모듈 경계](docs/architecture/module-boundaries.md)
- [데이터 소유권](docs/architecture/data-ownership.md)
- [RAG와 자격판정 흐름](docs/architecture/rag-and-eligibility-flow.md)
- [데이터 저장 구조](docs/data/storage-model.md)
- [Ollama와 pgvector](docs/rag/ollama-pgvector.md)
- [정책 모델](docs/domain/policy-model.md)
- [자격판정 모델](docs/domain/eligibility-model.md)
- [예외 처리](docs/domain/exception-handling.md)
- [보안 설계](docs/security/security-design.md)
- [데이터 분류](docs/security/data-classification.md)
- [ADR 작성 기준](docs/adr/README.md)
