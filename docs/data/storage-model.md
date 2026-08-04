# 데이터 저장 구조

## PostgreSQL 정형 데이터

MVP 기준 PostgreSQL은 다음 데이터 영역을 관리한다.

- `category`: 정책 분류.
- `policy`: 정책 메타데이터, 기관, 지역, 신청 기간, 상태, 버전.
- `question`: 사용자 사실 수집 질문.
- `user_fact`: 혼인 상태, 거주지, 소득, 자산, 주택 여부 등 사용자 사실과 확정 여부.
- `policy_rule`: 구조화된 정책 조건과 원문 근거 위치.
- `policy_evaluation`: 사용자 또는 세션별 판정 결과, 정책 버전, 사용자 사실 버전.
- `policy_relation`: 정책 간 관계와 그래프 Projection 기반.

실제 테이블명과 필드는 기존 데이터 설계 문서가 확인되면 그 정의를 우선한다. Phase 0에서는 이름을 구현 계약으로 확정하지 않는다.

## pgvector 검색 데이터

pgvector는 PostgreSQL 확장으로 다음 데이터를 관리한다.

- `policy_document`: FAQ, 공고문, 안내문, 정책 원문.
- `document_chunk`: 검색 단위 청크.
- `document_chunk_embedding`: Ollama 임베딩 벡터와 청크 연결.

별도의 Vector DB는 현재 도입하지 않는다.

## 버전 원칙

정책 원문, 구조화 조건, 사용자 사실, 판정은 각각 버전을 가져야 한다. 정책 원문이나 조건이 변경되면 기존 판정은 `STALE`로 처리한다.
