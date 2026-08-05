# 데이터 저장 구조

## PostgreSQL 정형 데이터

MVP 기준 PostgreSQL은 다음 데이터 영역을 관리한다.

- `category`: 정책 분류.
- `policy`: 정책 식별자, 정책명, 분류, 기관 같은 안정적인 정책 메타데이터.
- `policy_version`: 정책 버전, 적용 시작·종료일, 상태, 원문 해시, 게시 상태.
- `question`: 사용자 사실 수집 질문.
- `user_fact`: 혼인 상태, 거주지, 소득, 자산, 주택 여부 등 사용자 사실과 확정 여부.
- `policy_rule`: 구조화된 정책 조건과 원문 근거 위치. 적용 대상 `policy_version`을 참조한다.
- `policy_evaluation`: 사용자 또는 세션별 판정 결과, `policy_version`, 사용자 사실 버전.
- `policy_relation`: 정책 간 관계와 그래프 Projection 기반.

실제 테이블명과 필드는 기존 데이터 설계 문서가 확인되면 그 정의를 우선한다. Phase 0에서는 이름을 구현 계약으로 확정하지 않는다.

## 정책 CSV 기준 데이터

MVP 실행 기준 데이터는 `backend/data/policy-seed/`에 저장한다. 현재 기준본은 정책 38개, 질문 49개, Rule 133개, 관계 24개, RAG 문서 38개다.

- 백엔드는 시작 시 CSV ID 중복, 참조 무결성, 공식 URL 형식, 정책별 RAG 문서 존재 여부를 검증한다.
- 질문 option은 UI `label`과 사용자 사실/Rule 비교용 canonical `value`를 분리한다. Rule의 결정형 계산 가능 여부는 `evaluation_mode`로 명시한다.
- Rule Engine에 제공하는 결정형 Rule은 `evaluation_mode=DETERMINISTIC`이면서 `review_status=APPROVED`인 항목으로 제한한다. `DRAFT` Rule은 catalog에 보존하되 결정형 조회 결과에 포함하지 않는다.
- CSV header, enum 필드, boolean, ISO 날짜와 신청 기간 순서를 시작 시 fail-fast로 검증한다.
- `SHA256SUMS`는 기준본 11개 파일의 저장소 내 변경을 검증한다.
- CSV는 읽기 전용이며 API 요청 중 변경하지 않는다.
- 사용자 사실 및 평가 template CSV는 스키마 참고용 빈 파일이며 개인정보를 저장하지 않는다.

D0 [Raw Policy Schema](raw-policy-schema.md)는 과거 수집 계약 기록으로 남지만 현재 런타임 경로에는 사용하지 않는다. 제공된 CSV에는 원문 파일 해시가 없으므로 자동 변경 감지는 지원하지 않으며 `verified_at`과 저장소 diff로 변경을 검수한다.

수동 원문 재검수와 Seed 갱신은 [정책 Seed 운영 가이드](policy-seed-operations.md)를 따른다.

## pgvector 검색 데이터

pgvector는 PostgreSQL 확장으로 다음 데이터를 관리한다.

- `policy_document`: FAQ, 공고문, 안내문, 정책 원문. 적용 대상 `policy_version`을 참조한다.
- `document_chunk`: 검색 단위 청크.
- `document_chunk_embedding`: Ollama 임베딩 벡터와 청크 연결.

별도의 Vector DB는 현재 도입하지 않는다.

## 버전 원칙

정책 원문, 구조화 조건, 사용자 사실, 판정은 각각 버전을 가져야 한다. 정책 원문이나 조건이 변경되면 기존 판정은 `STALE` 평가 상태로 처리한다.

MVP부터 정책 변경 추적은 별도 `policy_version`으로 관리한다. `verified_at` 날짜나 원문 해시는 버전의 속성일 수 있지만 버전 식별자를 대체하지 않는다.
