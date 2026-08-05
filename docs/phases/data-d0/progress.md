# Data Phase D0 Progress

## Status

Implemented on branch `phase-d0-raw-policy-schema`.

## Completed Work

- JSON Schema와 Python 타입으로 Raw metadata 1.0 필드와 검증 규칙을 정의했다.
- 공식 출처 `OFFICIAL`과 기사·요약 등 2차 출처 `SECONDARY`를 구분했다.
- 요구된 원본 검수 상태 6종을 코드와 문서에 고정했다.
- exact-byte SHA-256 함수와 UTC 날짜 기반의 결정적 Raw/sidecar 경로 생성을 구현했다.
- 고유 `collection_id`와 전체 SHA-256을 경로에 포함해 동일 콘텐츠의 복수 수집 이력과 sidecar를 분리했다.
- canonical source URL만 허용하고 query와 fragment가 메타데이터에 저장되지 않도록 검증했다.
- Python 직렬화 필드와 enum이 JSON Schema와 동기화되는 계약 테스트를 추가했다.
- Raw/Processed 분리, immutable Raw, 파생 산출물의 원본 참조 원칙을 확정했다.
- credential/secret URL과 경로가 포함된 원본 파일명을 거부하도록 경계 검증을 추가했다.
- 정책 수집에서 개인정보를 제외하고 공개 원문의 불필요한 연락처가 Processed/LLM 입력으로 전파되지 않도록 기준을 문서화했다.

## Deferred

- 현재 저장소에는 SQLAlchemy와 Alembic이 없으며 B0에서도 명시적으로 후속 Phase로 연기했다. D0는 파일 기반 수집 원본 계약이므로 migration을 추가하지 않았다.
- 상태 전이 권한과 감사 이벤트, 실제 수집 전송 메타데이터, 관리자 검수 기능은 구현 Phase로 연기했다.
- Processed 산출물의 개별 스키마는 각 추출·정규화 Phase에서 정의한다.
