# Backend Phase 1 Verification

## 로컬 Backend

| 항목 | 명령 | 결과 | 비고 |
| --- | --- | --- | --- |
| uv lock | `cd backend && UV_CACHE_DIR=../.uv-cache uv lock` | 통과 | Python 3.11 기준 lock 생성 |
| uv sync | `cd backend && UV_CACHE_DIR=../.uv-cache uv sync --extra dev --frozen` | 통과 | `backend/.venv` 생성, Git ignore 확인 |
| backend test | `cd backend && UV_CACHE_DIR=../.uv-cache uv run pytest` | 통과 | 14 passed |
| backend lint | `cd backend && UV_CACHE_DIR=../.uv-cache uv run ruff check app tests` | 통과 | All checks passed |
| local app run | `cd backend && UV_CACHE_DIR=../.uv-cache uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload` | 통과 | 앱 기동 확인 |
| health | `curl -i http://127.0.0.1:8000/health` | 통과 | 200 OK |
| swagger | `curl -I http://127.0.0.1:8000/` | 통과 | 200 OK, `text/html` |

## Docker Compose

| 항목 | 명령 | 결과 | 비고 |
| --- | --- | --- | --- |
| compose config | `docker compose config --quiet` | 통과 | 설정 파싱 성공 |
| backend build | `docker compose build backend` | 통과 | uv 기반 이미지 빌드 |
| full compose up | `docker compose up --build -d` | 통과 | postgres, ollama, backend, frontend up |
| compose run test | `docker compose run --rm backend pytest` | 통과 | 14 passed |
| compose run lint | `docker compose run --rm backend ruff check app tests` | 통과 | All checks passed |
| compose backend run | `docker compose up --build -d postgres backend` | 통과 | postgres healthy, backend up |
| container health | `docker compose exec backend python -c "... /health ..."` | 통과 | 200 OK |
| container swagger | `docker compose exec backend python -c "... / ..."` | 통과 | 200 OK, `text/html` |

## Repository

| 항목 | 명령 | 결과 |
| --- | --- | --- |
| structure | `scripts/verify-structure.sh` | 통과 |
| markdown links | `python3 scripts/check-doc-links.py` | 통과 |
| whitespace | `git diff --check` | 통과 |
| ignored local files | `git status --short --ignored` | 통과. `.env`, `.uv-cache/`, `backend/.venv/`, caches ignored |

## Migration

Alembic migration은 현재 저장소에 존재하지 않으며 Phase 1 범위에서도 ORM 모델과 migration을 만들지 않는다. 따라서 migration 검증은 해당 없음.

## 제한사항

Host `localhost:8000`은 다른 로컬 프로젝트 프로세스가 점유 중일 수 있다. 이 경우 Docker backend 검증은 컨테이너 내부 localhost 호출로 확인한다. 재현과 해결 기준은 [Backend Phase 1 Port Conflict](../../troubleshooting/backend-phase-1-port-conflict.md)에 기록했다.
