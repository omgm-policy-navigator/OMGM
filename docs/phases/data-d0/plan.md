# Data Phase D0 Plan

## Goal

정책 수집에서 어떤 데이터를 원본으로 보존하고 무엇을 가공할지 결정한다.

## Scope

- Raw Policy Schema
- 공식·2차 출처 구분
- 수집 메타데이터와 원문 해시 기준
- `COLLECTED`, `EXTRACTED`, `REVIEWING`, `APPROVED`, `REJECTED`, `OUTDATED` 검수 상태
- Raw/Processed 파일명과 폴더 규칙
- 개인정보 미수집 기준
- 계약 검증과 경로 생성 단위 테스트

## Completion Criteria

- Raw와 Processed 저장 위치와 변경 책임이 분리된다.
- 2차 기사와 공식 정책 문서가 명시적으로 구분된다.
- exact-byte SHA-256, UTC 수집 시각, 출처 URL·게시자 저장 기준이 확정된다.
- 계약 검증 테스트와 저장소의 적용 가능한 검증을 통과한다.

## Out of Scope

- 외부 API/웹 수집기와 인증키 연동
- 텍스트 추출, 조건 후보 생성, LLM, 청크와 임베딩
- 관리자 검수 UI/API와 상태 전이 서비스
- SQLAlchemy 모델, Alembic migration, 게시 정책 DB 반영
