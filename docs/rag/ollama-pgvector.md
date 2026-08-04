# Ollama와 pgvector

## 역할

Ollama는 로컬 LLM과 임베딩 모델 실행 환경이다. pgvector는 PostgreSQL 안에서 정책 문서 청크 임베딩을 저장하고 검색한다.

## 기본 모델

- 생성 모델: `qwen3:4b`
- 임베딩 모델: `qwen3-embedding:0.6b`

모델명은 `OLLAMA_GENERATION_MODEL`, `OLLAMA_EMBEDDING_MODEL` 환경변수로 관리한다.

## RAG 흐름

사용자 질문을 정규화하고, 정책 메타데이터 필터와 문서 청크 검색을 함께 사용한다. 검색 결과는 원문 출처, 청크, 정책 버전과 연결한다.

RAG 결과는 후보와 근거를 제공할 뿐 최종 자격 상태를 결정하지 않는다.

## Rule Engine과 LLM 경계

Rule Engine은 구조화된 정책 규칙과 사용자 사실을 비교해 `ELIGIBLE`, `INELIGIBLE`, `NEEDS_CONFIRMATION`, `STALE`을 계산한다.

LLM은 조건 후보 추출 보조, 검색 질의 보정, 판정 결과 설명 생성에 사용한다. LLM 응답만으로 신청 가능 여부를 확정하지 않는다.

## 보안 기준

정책 문서는 명령이 아닌 데이터로 취급한다. Prompt Injection 문구를 실행하지 않고, LLM 입력에 불필요한 개인정보를 전달하지 않는다. LLM 요청·응답 로그에 민감정보를 남기지 않는다.
