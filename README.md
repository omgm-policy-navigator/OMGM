# 나만 결혼해?

결혼·신혼부부 지원정책을 정책 원문과 구조화된 조건에 근거해 탐색하고 자격 상태를 판정하는 서비스입니다.

## 저장소 구조

- `frontend/`: React Web 사용자 인터페이스.
- `backend/`: FastAPI 모듈러 모놀리스 API.
- `data-pipeline/`: 정책 데이터 수집·구조화·청크·임베딩 준비 CLI.
- `infra/`: PostgreSQL, pgvector, Ollama 로컬 인프라.
- `docs/`: 제품, 아키텍처, 도메인, 데이터, RAG, 보안, 개발 추적 문서.
- `scripts/`: 반복 검증용 보조 스크립트.
- `sample-data/`: 비민감 샘플 입력.

## 주요 구성 요소

- React + Vite + TypeScript
- FastAPI
- Python 3.11+
- PostgreSQL + pgvector
- Ollama
- Docker Compose
- Node.js 22+

## 환경변수 준비

```bash
cp .env.example .env
```

`.env.example`의 `POSTGRES_PASSWORD=change-me`는 로컬 예제값이다. 운영 기본값으로 사용하지 않는다.

## 전체 로컬 실행

```bash
docker compose up --build
```

로컬 인프라만 먼저 실행:

```bash
docker compose up -d postgres ollama
```

## 개별 실행

백엔드:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

프론트엔드:

```bash
cd frontend
npm install
npm run dev
```

데이터 파이프라인:

```bash
cd data-pipeline
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m policy_pipeline.main --sample ../sample-data/sample-policy.json
```

Health Check:

```bash
curl http://localhost:8000/health
```

## 전체 테스트

```bash
scripts/test-all.sh
```

개별 명령은 [Backend](backend/README.md), [Frontend](frontend/README.md), [Data Pipeline](data-pipeline/README.md)를 확인한다.

## 핵심 문서

- [제품 개요](docs/product/product-overview.md)
- [사용자 시나리오](docs/product/user-scenarios.md)
- [MVP 범위](docs/product/mvp-scope.md)
- [시스템 개요](docs/architecture/system-overview.md)
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
- [Phase 0 기록](docs/development/phase-0-foundation.md)
- [개발 추적 기준](docs/development/development-tracking.md)
- [ADR 작성 기준](docs/adr/README.md)

현재 개발 Phase: Phase 0 Project Foundation.
