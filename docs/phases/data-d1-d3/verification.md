# Analysis Phase D1-D3 Verification

## 자동 검증

- `docker compose -f compose.yaml -f compose.dev.yaml config --quiet`: 통과
- `docker compose -f compose.yaml -f compose.dev.yaml run --build --rm backend alembic upgrade head`: 통과 (`20260805_0001`)
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest`: 73 passed (CSV 도메인 계약과 Windows CRLF/Linux LF 호환 회귀 테스트 포함)
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests`: 통과
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend npm test`: 1 passed
- Frontend Docker Lint, typecheck, build: 통과
- `python scripts/check-doc-links.py`: 통과
- `git diff --check`: 통과

## 데이터 제한

- 제공 CSV는 2026-08-05 검증 스냅샷이다. `SHA256SUMS`는 저장된 기준본 변경을 감지하지만 공식 사이트 원문 자체의 변경을 자동 감지하지 않는다.
- RAG 문서는 공식 URL을 연결한 정책 개요이며 전체 공고문 원문은 아니다.
- `evaluation_mode=OFFICIAL_CONFIRMATION_REQUIRED`인 31개 Rule은 공식 확인 전 확정 판정에 사용하지 않는다.
- `embedding` 열은 비어 있으며 실제 임베딩과 pgvector 적재는 후속 범위다.

## Migration

DB Schema 변경이 없으므로 신규 Alembic migration은 없다.

## Troubleshooting

기존 backend 이미지에서 Alembic 실행 파일이 보이지 않는 문제가 확인되어 [Docker backend image 재빌드](../../troubleshooting/docker-backend-image.md)에 기록했다.
