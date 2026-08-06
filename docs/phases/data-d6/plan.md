# Analysis Phase D6 Plan

## 목표

공식 정책 원문의 변경을 감지하되 검수 전 후보를 사용자·Rule Engine·RAG에 배포하지 않는다.

## 범위

- 공식 호스트 API/HTML/PDF 재수집과 실제 응답 크기 제한
- exact-byte SHA-256 비교와 구조화 필드 Diff
- 변경 필드 기반 Rule 영향 및 원문 변경 기반 Chunk 영향 식별
- `OUTDATED → REVIEWING → APPROVED` 검수 리포트
- 승인된 리포트만 별도 staging Seed로 재생성하고 전체 Seed 무결성 재검증
- 승인 시 검증된 Seed Patch를 리포트에 고정하고 재생성 manifest로 적용 범위를 추적

## 제외 범위

- FastAPI 요청 중 외부 수집
- 검수 후보의 운영 DB 자동 반영
- 자동 reindex·재판정 실행
- 관리자 UI와 스케줄러
