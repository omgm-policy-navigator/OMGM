# Backend Phase 1 Plan

## 목표

Backend 프로젝트의 기본 실행 환경을 `uv`, FastAPI, Docker Compose, PostgreSQL 설정 기반으로 정리한다.

## 포함 범위

- FastAPI 앱 패키지를 `backend/app` 구조로 정리.
- `backend/pyproject.toml`과 `backend/uv.lock` 기반 의존성 관리.
- PostgreSQL 연결 설정과 SQLAlchemy async engine 객체 추가.
- Dockerfile을 uv 기반 실행으로 변경.
- Docker Compose backend 실행 계약 유지.
- `/health`와 Swagger 접속 계약 문서화.
- backend 테스트와 lint 실행 경로 정리.

## 제외 범위

- Business Logic
- Repository
- ORM 모델
- Alembic migration
- 신규 비즈니스 API
- 인증
