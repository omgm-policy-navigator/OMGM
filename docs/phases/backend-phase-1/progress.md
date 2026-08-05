# Backend Phase 1 Progress

Status: DONE

## 완료

- `main` 최신화 후 `chore/backend-phase-1-init` 브랜치 생성.
- 기존 `backend/src/app` 패키지를 `backend/app`로 이동.
- `app/config`, `app/db`, `app/models`, `app/schemas`, `app/services` 경계 생성.
- `pydantic-settings` 기반 설정 로딩으로 전환.
- `DATABASE_URL` 기반 SQLAlchemy async engine 생성 함수 추가.
- Dockerfile을 uv 기반 실행으로 변경.
- README, AGENTS, backend contract, phase 문서 갱신.
- backend 테스트를 pytest 기준으로 정리.

## 검증 완료

- `uv lock`
- `uv run uvicorn app.main:app --reload`
- `GET /health`
- Swagger 접속
- Docker Compose config/build/run
- pytest, ruff, git diff check
