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

## 정책 수집 파일 데이터

데이터 파이프라인의 원문과 가공 산출물은 서로 다른 저장 루트를 사용한다.

- Raw: 수집 당시의 immutable bytes와 JSON sidecar metadata. 원문 해시, 수집 시각, 출처 구분, 검수 상태를 보존한다.
- Processed: Raw를 참조해 생성한 텍스트, 정규화 결과, 조건 후보, 청크, 임베딩 준비 산출물. Raw를 덮어쓰지 않는다.

필드, 상태, 출처 판정과 경로 계약은 [Raw Policy Schema](raw-policy-schema.md)를 따른다. 실제 원문 파일은 Git과 샘플 데이터에서 제외한다.

## pgvector 검색 데이터

pgvector는 PostgreSQL 확장으로 다음 데이터를 관리한다.

- `policy_document`: FAQ, 공고문, 안내문, 정책 원문. 적용 대상 `policy_version`을 참조한다.
- `document_chunk`: 검색 단위 청크.
- `document_chunk_embedding`: Ollama 임베딩 벡터와 청크 연결.

별도의 Vector DB는 현재 도입하지 않는다.

## 버전 원칙

정책 원문, 구조화 조건, 사용자 사실, 판정은 각각 버전을 가져야 한다. 정책 원문이나 조건이 변경되면 기존 판정은 `STALE` 평가 상태로 처리한다.

MVP부터 정책 변경 추적은 별도 `policy_version`으로 관리한다. `verified_at` 날짜나 원문 해시는 버전의 속성일 수 있지만 버전 식별자를 대체하지 않는다.
