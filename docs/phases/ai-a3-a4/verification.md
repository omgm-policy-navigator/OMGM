# AI Phase A3-A4 Verification

## 검증

- PR 리뷰 회귀·Seed 무결성 집중 테스트: `29 passed`
- 전체 백엔드 테스트: `163 passed, 1 skipped`
- Ruff (`src/app`, `tests`, 신규 migration): 통과
- Compose 설정 렌더링: 통과
- `git diff --check`: 통과
- Alembic 단일 Head: `20260806_0006`
- Alembic offline SQL: `vector(1024)` 테이블과 HNSW cosine index 생성 SQL 확인
- Docker Alembic 적용: Docker Desktop daemon이 실행 중이지 않아 미실행(`docker_engine` named pipe 없음)

## Migration

- `20260806_0006_rag_vector_index.py`
- `document_chunk`, `document_chunk_embedding`, HNSW cosine index 추가
- pgvector 통합 테스트는 Migration, 1024차원 저장, 잘못된 차원 거부, cosine 순서, stale Chunk·이전 모델 정리와 cascade를 검증한다. 로컬에서는 Docker daemon 부재로 skip됐으며 `DATABASE_URL`이 설정된 CI의 pgvector PostgreSQL에서 실행된다.

## Troubleshooting

실제 재사용 가능한 장애와 해결 과정이 확인될 때만 문서를 추가한다.
