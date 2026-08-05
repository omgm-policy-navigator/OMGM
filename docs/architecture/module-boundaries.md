# 모듈 경계

## `frontend/`

책임: 사용자 UI, 브라우저 상태, Backend REST/SSE 호출, 판정 결과와 정책 근거 표시.

입력: 사용자 입력, 백엔드 API 응답, SSE 이벤트.

출력: 화면 상태, API 요청.

금지 의존성: PostgreSQL 직접 접근, Ollama 직접 호출, 백엔드 내부 Python 코드 참조.

테스트 범위: 렌더링, 환경변수 로딩, 타입 검사, 빌드.

## `backend/app/api`

책임: FastAPI 라우터, Health Check, REST/SSE 경계, 안전한 오류 응답.

입력: HTTP 요청.

출력: JSON 응답, SSE 이벤트.

허용 의존성: `core`, 기능 모듈.

금지 의존성: 라우터 내부 SQL 작성, 라우터 내부 판정 규칙 구현.

테스트 범위: 앱 로딩, Health Check, 오류 응답 구조.

## `backend/app/core`

책임: 설정 로딩, 구조화 로그, 공통 오류, lifespan.

입력: 환경변수.

출력: `AppConfig`, JSON 로그, 공통 예외.

금지 의존성: UI, 데이터 파이프라인, 정책 판정 세부 규칙.

테스트 범위: 기본 설정, 잘못된 포트, 잘못된 로그 레벨.

## `backend/app/eligibility`

책임: 정책 규칙과 사용자 사실 비교, 충족·불충족·확인 필요 조건 계산, 판정 상태 계산.

입력: 구조화 정책 규칙, 사용자 사실, 정책 버전.

출력: `ELIGIBLE`, `INELIGIBLE`, `NEEDS_CONFIRMATION`, `STALE` 등 판정 결과.

금지 의존성: LLM 응답 문자열 기반 최종 판정, 자연어 설명 생성, HTTP 직접 처리.

테스트 범위: 정보 부족, 필수 조건 불충족, 충족, 답변 충돌, 정책 버전 변경.

## 향후 백엔드 기능 모듈

`conversation`, `questions`, `policies`, `rag`, `graph`, `saved_policies`, `notifications`는 실제 구현이 시작될 때 생성한다. Phase 0에서는 빈 폴더를 미리 만들지 않는다.

## `data-pipeline/`

책임: 정책 수집, 파싱, 정규화, 조건 후보 추출, 청크, 임베딩 준비, 검수 상태 준비.

입력: 원천 정책 데이터, 샘플 JSON, 환경변수.

출력: 내부 정책 모델 후보, 청크 후보, 임베딩 저장 대상.

금지 의존성: 프론트엔드 코드, API 요청 처리 경로, 최종 사용자 응답 생성.

테스트 범위: 설정 로딩, 샘플 입력 처리.

## `infra/`

책임: Docker Compose 기반 로컬 PostgreSQL, pgvector, Ollama, 초기화 스크립트.

금지 의존성: 애플리케이션 비즈니스 로직.

테스트 범위: `docker compose config`, 초기화 스크립트 위치.
