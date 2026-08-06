# AI Phase A3-A4 Plan

## 목표

D4의 승인 Chunk를 `qwen3-embedding:0.6b`로 임베딩해 PostgreSQL pgvector에 중복 없이 적재하고, 선택한 활성 정책의 공식 승인 근거만 유사도 검색한다.

## 범위

- 1024차원 Ollama 임베딩 호출 및 출력 검증
- A3 Chunk 유형(`OVERVIEW`, `ELIGIBILITY`, `APPLICATION`, `DOCUMENTS`, `FAQ`, `CAUTION`) 매핑
- Chunk 메타데이터와 모델별 벡터 저장
- 문서 단위 재색인과 제거된 Chunk 정리
- 정책 ID·문서 상태·신뢰도·정책 상태·임베딩 모델 필터
- Top K, 코사인 유사도 임계값, Citation과 근거 부족 결과

## 제외 범위

- 외부 원문 자동 수집
- LLM 답변 생성과 HTTP 검색 API
- Rule Engine 자격 상태 변경
- Hybrid lexical reranking
