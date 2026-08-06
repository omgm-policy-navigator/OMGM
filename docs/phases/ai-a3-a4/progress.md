# AI Phase A3-A4 Progress

## 완료 작업

- 부모 문서가 `APPROVED`·`OFFICIAL`이고 Chunk가 `APPROVED`이며 정책이 `ACTIVE`인 28개 문서만 재색인 입력으로 읽는다. Chunk의 정책 ID·문서 유형·URL이 부모 문서와 다르면 적재를 중단한다.
- Ollama `/api/embed` 배치 호출 결과의 개수, 1024차원과 유한 숫자를 검증한다.
- `document_chunk`와 `document_chunk_embedding`을 분리하고 Chunk·모델별 upsert 계약을 구현했다.
- 같은 문서를 다시 색인하면 기존 Chunk를 갱신하고 사라진 Chunk를 삭제한다. 전체 동기화에서 현재 유효 문서 집합 밖의 삭제·비활성·비승인 문서도 제거한다.
- 모델이 변경되면 같은 Chunk의 이전 모델 벡터를 제거한다.
- 문서별 repository는 `flush`만 수행하고 전체 재색인이 성공한 뒤 상위 실행 경계에서 한 번 commit한다. 실패 시 전체 rollback한다.
- 벡터 검색 SQL에서 선택 정책, `APPROVED`, `OFFICIAL`, `ACTIVE`, 임베딩 모델을 모두 필터링한다.
- Top K는 1~20, 유사도 임계값은 0~1로 제한하고 결과가 없으면 `insufficient_evidence=true`를 반환한다.
- Citation에 문서·Chunk·정책 버전·URL·원문 위치·제한된 excerpt를 포함한다.

## 실행

```bash
cd backend
python -m app.modules.rag.reindex
```

재색인에는 PostgreSQL과 `qwen3-embedding:0.6b`가 설치된 Ollama가 필요하다.

## 제한사항

- 현재 D4 기준본은 정책별 Overview Chunk 1개만 제공하므로 실제 검색 품질 평가는 세부 원문 Chunk 확충 후 다시 수행해야 한다.
- A4는 Vector 검색만 구현한다. 키워드 결합과 reranking은 이번 범위가 아니다.
- 검색용 HTTP API와 답변 생성 연결은 후속 오케스트레이션 범위다.
- 실제 pgvector 통합 테스트는 `DATABASE_URL`이 제공되는 CI PostgreSQL에서 실행되며 로컬 DB가 없으면 skip된다.
