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

## 테스트

```bash
cd backend
source .venv/bin/activate
python -m unittest discover
```

## 환경변수

루트 `.env.example`의 `BACKEND_*`, `DATABASE_URL`, `OLLAMA_*`, `LLM_TIMEOUT_SECONDS` 값을 사용합니다. PostgreSQL과 Ollama는 로컬 실행 시 `compose.yaml`로 기동합니다.
