# 모듈 경계

## `frontend/`

책임: 사용자 UI, 브라우저 상태, Backend REST/SSE 호출, 판정 결과와 정책 근거 표시.

입력: 사용자 입력, 백엔드 API 응답, SSE 이벤트.

출력: 화면 상태, API 요청.

금지 의존성: PostgreSQL 직접 접근, Ollama 직접 호출, 백엔드 내부 Python 코드 참조.

테스트 범위: 렌더링, 환경변수 로딩, 타입 검사, 빌드.

## `backend/src/app/api`

책임: FastAPI 라우터, Health Check, REST/SSE 경계, 안전한 오류 응답.

입력: HTTP 요청.

출력: JSON 응답, SSE 이벤트.

허용 의존성: `core`, 기능 모듈.

금지 의존성: 라우터 내부 SQL 작성, 라우터 내부 판정 규칙 구현.

테스트 범위: 앱 로딩, Health Check, 오류 응답 구조.

## `backend/src/app/core`

책임: 설정 로딩, 구조화 로그, 공통 오류, lifespan.

입력: 환경변수.

출력: `AppConfig`, JSON 로그, 공통 예외.

금지 의존성: UI, 데이터 파이프라인, 정책 판정 세부 규칙.

테스트 범위: 기본 설정, 잘못된 포트, 잘못된 로그 레벨.

## `backend/src/app/db`

책임: 데이터베이스 세션 설정, migration 연결, persistence helper, 트랜잭션 경계의 공통 기준.

입력: 설정값, repository 호출.

출력: 데이터베이스 연결과 persistence 결과.

금지 의존성: FastAPI Router 직접 참조, 분석 모듈에 SQLAlchemy Session 강제 전달, 프론트엔드 또는 파이프라인 코드 참조.

테스트 범위: 설정 로딩, migration 연결, repository contract.

## `backend/src/app/modules`

책임: 대화, 질문, 정책 조회, RAG, 그래프 Projection, 저장 정책, 알림, 사용자 사실, 판정 결과 같은 기능 모듈의 소유 경계.

입력: API DTO, 저장소 조회 결과, Rule Engine 결과, LLM/RAG 보조 결과.

출력: API 응답 DTO에 매핑 가능한 module result.

금지 의존성: 기능 없는 대량 폴더 생성, SQL을 라우터로 유출, API 응답 Schema와 DB Entity 직접 공유.

테스트 범위: 기능별 unit test, API와 DB를 분리한 contract test.

## `backend/src/app/llm`

책임: Ollama 호출, LLM timeout 설정 적용, 질문 이해 보조, 검색 질의 보정, 설명 생성 보조에 필요한 DTO와 client 경계.

입력: 최소화된 prompt DTO, 정책 근거 요약, 설정값.

출력: 구조화 후보 또는 설명 초안.

금지 의존성: 최종 자격 상태 결정, 금융·소득·자산 원천 거래 직접 전달, 정책 근거 없는 생성.

테스트 범위: timeout/config 적용, fake client contract, 민감정보 최소화.

## `backend/src/app/modules/eligibility`

책임: 평가 use case 경계, 정책 규칙과 사용자 사실 비교, 충족·불충족·확인 필요 조건 계산, 신청 가능성 상태 계산.

입력: 구조화 정책 규칙, 사용자 사실, `policy_version`.

출력: `LIKELY_ELIGIBLE`, `LIKELY_INELIGIBLE`, `NEEDS_CONFIRMATION` 등 신청 가능성 결과와 별도 evaluation state.

금지 의존성: LLM 응답 문자열 기반 최종 판정, 자연어 설명 생성, HTTP 직접 처리, 다른 평가 facade와 책임 중복.

테스트 범위: 정보 부족, 필수 조건 불충족, 충족, 답변 충돌, 정책 버전 변경.

## `backend/src/app/modules/policies`

책임: `backend/data/policy-seed`의 검수된 CSV를 읽기 전용으로 로딩하고 ID·참조·URL·RAG 문서 연결을 검증한다.

출력: Policy Seed Catalog, 결정형 평가 가능 Rule, 공식 확인 필요 Rule, RAG 문서 DTO.

금지 의존성: FastAPI Router, SQLAlchemy Session, 외부 원문 수집, CSV 변경.

## 향후 백엔드 기능 모듈

`conversation`, `questions`, `rag`, `graph`, `saved_policies`, `notifications`는 실제 구현이 시작될 때 생성한다. `policies`는 CSV 기준 데이터 로딩 구현이 시작되어 생성되었다.

## `backend/data/policy-seed/`

책임: 관리자 검수를 마친 MVP 정책 CSV 기준본. 별도 수집·정규화 실행 과정 없이 백엔드가 직접 읽는다.

입력: 저장소 변경으로 승인된 CSV 파일.

출력: 정책·질문·Rule·관계·RAG 문서 기준 데이터.

금지 사항: 개인정보 저장, 런타임 변경, placeholder 기준을 확정값으로 해석.

## `infra/`

책임: Docker Compose 기반 로컬 PostgreSQL, pgvector, Ollama, 초기화 스크립트.

금지 의존성: 애플리케이션 비즈니스 로직.

테스트 범위: `docker compose config`, 초기화 스크립트 위치.

## `backend/src/app/modules/user_facts`

책임: 자유 입력 조건 추출 Prompt, 허용 Enum 검증, Confidence 기반 확인 필요 판정, 기존 확정 사실과의 충돌 후보 탐지.

입력: 최소화된 사용자 자유 입력, 추출 전용 LLM JSON 응답, 기존 사용자 사실 DTO.

출력: 검증된 추출 후보, `requires_confirmation`, 충돌 후보.

금지 사항: FastAPI Router 또는 SQLAlchemy Session 의존, 추출 후보 직접 저장, 허용되지 않은 키 통과, 모호한 값을 확정 사실로 승격, 자격 상태 계산.
