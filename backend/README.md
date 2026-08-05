# Backend

FastAPI 기반 모듈러 모놀리스 백엔드입니다. 대화 오케스트레이션, 질문 엔진, 정책 조회, Rule Engine, RAG, 그래프 Projection, 저장 정책, 알림은 하나의 애플리케이션 내부 모듈로 확장합니다.

## 실행

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health Check:

```bash
curl http://localhost:8000/health
```

API 문서는 실행 후 `http://localhost:8000/docs`에서 확인합니다.

## 구조

백엔드는 `backend/src/app`를 import root로 사용하는 FastAPI 모듈러 모놀리스입니다.

- `app/api`: FastAPI 라우터, REST/SSE 경계, 안전한 오류 응답.
- `app/core`: 설정, 로깅, lifespan, 공통 오류.
- `app/db`: DB 세션과 persistence 설정 경계.
- `app/modules`: 기능 모듈 경계.
- `app/llm`: Ollama/LLM 호출 경계.
- `app/eligibility`: 구조화된 규칙과 사용자 사실을 비교하는 Rule Engine.

상세 책임과 API 초안은 [Backend Architecture](../docs/architecture/backend.md)와 [API Contracts](../docs/architecture/api-contracts.md)를 확인합니다.

## 테스트

```bash
cd backend
source .venv/bin/activate
python -m unittest discover -s tests
```

테스트는 `tests/unit`, `tests/integration`, `tests/fixtures`로 구분합니다. Fixture에는 실제 개인정보, 실제 소득·자산 정보, 실제 정책 신청 정보를 넣지 않습니다.

## 환경변수

루트 `.env.example`의 `BACKEND_*`, `DATABASE_URL`, `OLLAMA_*`, `LLM_TIMEOUT_SECONDS` 값을 사용합니다. PostgreSQL과 Ollama는 로컬 실행 시 `compose.yaml`로 기동합니다.
