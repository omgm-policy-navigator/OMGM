# Analysis Phase D6 Progress

Implemented on `analysis-d6-change-detection`.

## 완료

- FastAPI·SQLAlchemy에 의존하지 않는 `app.modules.policy_changes`를 추가했다.
- 공식 호스트·미디어 타입·응답 크기를 제한하는 API/HTML/PDF collector를 구현했다.
- HTML/PDF/API exact-byte SHA-256 변경과 nullable 보존 필드 Diff를 구현했다.
- 변경 필드와 Rule dependency, 문서 변경과 Chunk를 연결한 영향 분석을 구현했다.
- 원문을 포함하지 않는 JSON 검수 이력 리포트와 강제 상태 전이를 구현했다.
- 승인 전 Seed 생성을 차단하고 승인 후 별도 디렉터리 생성·checksum 갱신·전체 로더 검증을 구현했다.
- 활성 Seed와 운영 DB를 자동 변경하지 않는다.
