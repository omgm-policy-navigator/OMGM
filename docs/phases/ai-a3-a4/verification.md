# AI Phase A3-A4 Verification

## 검증

- A3/A4 및 관련 설정 집중 테스트: `33 passed`
- 전체 백엔드 테스트: `160 passed`
- Ruff (`src/app`, `tests`, 신규 migration): 통과
- Compose 설정 렌더링: 통과
- `git diff --check`: 통과
- Alembic 단일 Head: `20260806_0006`
- Alembic offline SQL: `vector(1024)` 테이블과 HNSW cosine index 생성 SQL 확인
- Docker Alembic 적용: Docker Desktop daemon이 실행 중이지 않아 미실행(`docker_engine` named pipe 없음)

## Migration

- `20260806_0006_rag_vector_index.py`
- `document_chunk`, `document_chunk_embedding`, HNSW cosine index 추가
- 실제 PostgreSQL upgrade/downgrade와 Ollama 재색인은 Docker daemon 제한으로 실행하지 못했다.

## Troubleshooting

실제 재사용 가능한 장애와 해결 과정이 확인될 때만 문서를 추가한다.
