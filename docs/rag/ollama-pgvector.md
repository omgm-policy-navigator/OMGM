# Ollama와 pgvector

## 역할

Ollama는 로컬 LLM과 임베딩 모델 실행 환경이다. pgvector는 PostgreSQL 안에서 정책 문서 청크 임베딩을 저장하고 검색한다.

## 기본 모델

- 생성 모델: `qwen3:4b`
- 임베딩 모델: `qwen3-embedding:0.6b`

모델명은 `OLLAMA_GENERATION_MODEL`, `OLLAMA_EMBEDDING_MODEL` 환경변수로 관리한다.

## RAG 흐름

사용자 질문을 정규화하고, 선택 분야·정책 메타데이터·구조화 Rule로 선정된 정책에 대해 문서 청크 검색을 사용한다. 검색 결과는 원문 출처, 청크, `policy_version`과 연결한다.

RAG 결과는 승인된 공식 근거를 제공할 뿐 정책 자격 후보나 최종 자격 상태를 결정하지 않는다.

## Rule Engine과 LLM 경계

Rule Engine은 구조화된 정책 규칙과 사용자 사실을 비교해 `LIKELY_ELIGIBLE`, `LIKELY_INELIGIBLE`, `NEEDS_CONFIRMATION` 같은 신청 가능성 상태를 계산한다. 정책 버전 변경, 답변 충돌, 미평가 상태는 별도 evaluation state로 관리한다.

LLM은 조건 후보 추출 보조, 검색 질의 보정, 행정 용어 설명, 판정 결과 요약 생성에 사용한다. LLM 응답만으로 신청 가능 여부를 확정하지 않는다. AI 출력과 fallback은 [AI 계약](../architecture/ai-contracts.md)을 따른다.

## 보안 기준

정책 문서는 명령이 아닌 데이터로 취급한다. Prompt Injection 문구를 실행하지 않고, LLM 입력에 불필요한 개인정보를 전달하지 않는다. LLM 요청·응답 로그에 민감정보를 남기지 않는다.

## D4 Embedding Seed

`backend/data/policy-seed/10_policy_document_chunk.csv`가 임베딩 전 입력 기준본이다. 각 행은 정책·문서 ID, 문서·Chunk 유형, 제목, 본문, 원문 URL, 원문 위치, 품질 상태와 콘텐츠 SHA-256을 포함한다. `quality_status=APPROVED`인 행만 후속 임베딩 작업에 전달한다.

D4 CSV의 `embedding` 열은 기준본이므로 계속 비워 둔다. A3는 `quality_status=APPROVED`이고 정책 상태가 `ACTIVE`인 행만 `qwen3-embedding:0.6b`의 1024차원 벡터로 생성해 `document_chunk`와 `document_chunk_embedding`에 적재한다.

동일 문서는 Chunk ID upsert와 문서별 stale Chunk 삭제로 재색인하며, 모델별 벡터는 `(chunk_id, model)`이 유일하다. 실행 명령은 `cd backend && python -m app.modules.rag.reindex`다.

## A4 검색 계약

검색 SQL은 `policy_id`, `document_status=APPROVED`, `trust_level=OFFICIAL`, `policy_status=ACTIVE`, 현재 임베딩 모델을 동시에 필터링한다. 코사인 유사도 임계값 아래 결과와 다른 정책·비활성 정책 근거는 반환하지 않는다. 결과에는 원문 URL과 위치, 정책 버전, Chunk ID가 포함되며 결과가 없으면 근거 부족으로 처리한다.
