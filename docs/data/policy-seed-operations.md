# 정책 Seed 운영 가이드

## 목적

자동 원문 수집기가 없는 MVP에서 공식 사이트 변경을 수동으로 확인하고, 검수된 CSV 기준본을 안전하게 갱신하는 절차다.

## 점검 시점

- 배포 전에는 38개 정책의 `source_url`과 `application_url`을 확인한다.
- `verified_at`으로부터 30일이 지난 정책은 다음 배포 전에 다시 확인한다.
- 모집형·예산형 정책은 새 공고 게시 또는 접수 시작 전에 우선 확인한다.
- URL 장애, 정책 종료, 기준 변경을 발견하면 해당 정책을 사용하는 판정을 재검토한다.

## 갱신 절차

1. 공식 기관 URL에서 정책명, 운영기관, 신청 기간, 금액·소득·자산 기준을 확인한다.
2. 변경된 정책·질문·Rule·문서 CSV를 함께 수정한다.
3. 결정형으로 검수된 Rule만 `evaluation_mode=DETERMINISTIC`, `review_status=APPROVED`로 둔다.
4. 공고 또는 공식 확인이 남은 Rule은 `evaluation_mode=OFFICIAL_CONFIRMATION_REQUIRED`, `review_status=DRAFT`로 둔다.
5. 정책의 `verified_at`을 실제 확인일로 변경하고 `SHA256SUMS`를 LF 정규화 bytes 기준으로 갱신한다.
6. Docker에서 migration, pytest, Ruff를 실행하고 PR 리뷰를 받는다.

## URL 및 임베딩 제한

현재 URL 유효성 자동 점검과 embedding 생성은 구현하지 않는다. URL 점검 자동화와 pgvector 적재는 별도 후속 이슈로 관리해야 한다. 이슈가 연결되기 전까지 위 수동 점검을 배포 체크리스트로 사용한다.

RAG 검색 API는 아직 없다. D4부터 검수된 Chunk Seed는 존재하지만 실제 embedding은 비어 있다. 후속 구현은 embedding이 없을 때 vector query를 실행하지 않고 `INSUFFICIENT_EVIDENCE`와 빈 citations를 반환해야 한다.

정책 문서 내용을 변경하면 연결된 `10_policy_document_chunk.csv`의 Chunk, `source_location`, `content_hash`, 품질 상태를 함께 재검수하고 `SHA256SUMS`를 갱신한다. 신청 조건과 신청 방법이 같은 Chunk에 섞이거나 출처 위치가 없는 행은 `APPROVED`로 두지 않는다.
