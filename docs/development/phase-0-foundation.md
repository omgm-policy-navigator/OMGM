# Phase 0 Foundation

## 목표

확정된 「나만 결혼해?」 설계를 공식 Markdown 문서로 재구성하고, React Web, FastAPI Backend, 정책 데이터 파이프라인, PostgreSQL + pgvector, Ollama 로컬 인프라를 단일 저장소 구조로 구성한다.

## 작업 범위

- 제품, 아키텍처, 도메인, 보안, 개발 추적 문서 작성.
- `frontend/`, `backend/`, `data-pipeline/`, `infra/`, `docs/` 중심의 단일 저장소 구조 구성.
- FastAPI Health Check, 설정 로딩, 구조화 로그, 대표 오류 응답 구성.
- React Web 최소 화면, 환경변수 기반 Backend URL 표시, 렌더링 테스트 구성.
- 정책 파이프라인 CLI, 설정 로딩, 샘플 입력 처리 구성.
- PostgreSQL + pgvector, Ollama Docker Compose 구성.
- Git ignore, 환경변수 예제, 런타임 버전, 의존성 관리 파일 구성.

## 생성·수정 파일

- `README.md`: 실행 진입점, 테스트 방법, 환경변수, 핵심 문서 링크.
- `AGENTS.md`: 프로젝트, 아키텍처, 코드, 테스트, 문서 규칙.
- `.gitignore`: 비밀정보, 가상환경, 빌드 산출물, 로그, 로컬 데이터를 제외.
- `.env.example`: 로컬 실행에 필요한 예제 환경변수.
- `.python-version`: Python 3.11 런타임 기준.
- `compose.yaml`: 로컬 PostgreSQL, pgvector, Ollama, backend, frontend 구성.
- `frontend/`: Vite + React + TypeScript 최소 앱과 테스트.
- `backend/`: FastAPI 앱, Health Check, 설정, 로그, 오류, eligibility 규칙, 테스트.
- `data-pipeline/`: 정책 파이프라인 CLI, 샘플 처리, 테스트.
- `infra/`: PostgreSQL pgvector 초기화와 Ollama 모델 준비 문서.
- `scripts/`: 전체 테스트와 구조 검증 스크립트.
- `sample-data/`: 비민감 샘플 정책 JSON.
- `docs/product/`: 제품 정의, 사용자 시나리오, MVP 범위.
- `docs/architecture/`: 단일 저장소 시스템 흐름, 모듈 경계, 데이터 소유권, RAG와 판정 책임.
- `docs/data/`: PostgreSQL과 pgvector 저장 구조 기준.
- `docs/rag/`: Ollama와 pgvector 책임 기준.
- `docs/domain/`: 정책 모델, 자격판정 모델, 예외 처리.
- `docs/security/`: 보안 설계와 데이터 분류.
- `docs/development/`: Phase 기록과 개발 추적 기준.
- `docs/adr/README.md`: ADR 작성 기준.

## 주요 결정

확정 아키텍처에 따라 단일 저장소를 유지하고, 백엔드는 FastAPI 모듈러 모놀리스로 구성한다. 프론트엔드는 Vite + React + TypeScript를 사용한다. 정책 데이터 수집은 `data-pipeline/`의 CLI·배치 책임으로 분리하고, 백엔드 요청 처리 경로에 넣지 않는다.

PostgreSQL과 pgvector는 같은 PostgreSQL 인스턴스에서 관리하고, 별도 Vector DB나 Graph DB는 도입하지 않는다. Ollama 모델명은 환경변수로 관리하며, LLM은 최종 판정을 결정하지 않는다.

## 검증 결과

| 검증 항목 | 명령 | 결과 | 비고 |
| --- | --- | --- | --- |
| Backend 설치 | `cd backend && python3.11 -m venv .venv && python -m pip install -e .` | 통과 | FastAPI 설치에 PyPI 네트워크 승인이 필요했음 |
| Backend 테스트 | `cd backend && python -m unittest discover` | 통과 | 12 tests |
| Backend 실행 | `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` | 통과 | 샌드박스 밖 localhost 바인딩 승인 필요 |
| Health Check | `curl http://localhost:8000/health` | 통과 | `{"status":"ok","service":"omgm-backend","environment":"local"}` |
| Pipeline 설치 | `cd data-pipeline && python3.11 -m venv .venv && python -m pip install -e .` | 통과 | build dependency 확인에 PyPI 네트워크 승인이 필요했음 |
| Pipeline 테스트 | `cd data-pipeline && python -m unittest discover` | 통과 | 2 tests |
| Pipeline 샘플 실행 | `cd data-pipeline && python -m policy_pipeline.main --sample ../sample-data/sample-policy.json` | 통과 | 샘플 정책 1건 처리 |
| Frontend 설치 | `cd frontend && npm install` | 통과 | `package-lock.json` 생성, 취약점 0 |
| Frontend 테스트 | `cd frontend && npm test` | 통과 | 1 test |
| Frontend 타입 검사 | `cd frontend && npm run typecheck` | 통과 | TypeScript 검사 통과 |
| Frontend 빌드 | `cd frontend && npm run build` | 통과 | Vite production build 통과 |
| 전체 테스트 | `scripts/test-all.sh` | 통과 | backend, pipeline, frontend test/typecheck/build |
| 구조 검증 | `scripts/verify-structure.sh` | 통과 | 루트 `src/` 제거 확인 |
| Compose 설정 | `docker compose config` | 통과 | PostgreSQL, pgvector, Ollama, backend, frontend 구성 파싱 |
| Compose 인프라 기동 | `docker compose up -d postgres ollama` | 부분 검증 | Docker 권한 승인 후 `pgvector/pgvector:pg16` pull 완료, `ollama/ollama:latest`가 1.8GB 이상 다운로드 중이라 중단. 실행 중인 서비스 없음 확인 |
| 문서 링크 | Markdown 상대 링크 검사 스크립트 | 통과 | 모든 상대 링크 유효 |
| whitespace | `git diff --check` | 통과 | 출력 없음 |
| Git ignore | `git check-ignore -v .env`, `backend/.venv`, `frontend/node_modules`, `frontend/dist` | 통과 | 비밀정보와 로컬 산출물 제외 |
| 비밀정보 | `git status --short --ignored`와 파일 내용 검토 | 통과 | 실제 Secret 없음. `.env.example`의 `change-me`는 로컬 예제값 |

## 미결 사항

- 외부 Notion 원문 접근은 현재 도구 미설치로 확인하지 못했다.
- 정책 데이터 공급처와 수집 주기 미확정.
- 정책 구조화 검증 방식 미확정.
- 개인정보 보존 기간과 필드 암호화 범위 미확정.
- 운영 Secret 관리 방식 미확정.
- 실제 PostgreSQL 스키마와 기존 데이터 설계 문서 대조 미완료.

## 다음 Phase 입력물

- 공식 제품·아키텍처·도메인·보안 문서.
- 모듈 경계와 데이터 소유권.
- 판정 상태 모델과 예외 처리 기준.
- 실행 가능한 React Web, FastAPI Backend, 정책 파이프라인 CLI.
- PostgreSQL + pgvector + Ollama 로컬 인프라.
- 테스트와 구조 검증 기반.
- 환경변수 계약.

## 관련 커밋과 PR

검증 후 커밋 해시, 원격 브랜치, PR 링크를 기록한다.
