# CI/CD

## CI

`CI` workflow는 pull request와 주요 브랜치 push에서 실행한다.

검증 범위:

- Backend 설치와 단위 테스트.
- Data Pipeline 설치, 단위 테스트, 샘플 실행.
- Frontend `npm ci`, 테스트, 타입 검사, 빌드.
- 저장소 구조 검증.
- Docker Compose 설정 검증.
- Markdown 링크 검증.
- whitespace 검사.
- `.env`가 Git 추적 대상이 아닌지 확인.

CI에서 사용하는 `.env`는 workflow 안에서 `.env.example`을 복사해 만든 임시 파일이다. 실제 Secret을 사용하지 않는다.

## CD

Phase 0에는 운영 배포 대상이 확정되지 않았다. 따라서 자동 배포는 구성하지 않는다.

`Release Readiness` workflow는 수동 실행 또는 `v*` 태그에서 backend/frontend Docker image build가 가능한지만 검증한다. 실제 registry push, 서버 배포, Secret 주입은 배포 대상과 운영 Secret 관리 방식이 확정된 뒤 추가한다.

## 보안 기준

- GitHub Actions에는 실제 DB 비밀번호, API 키, 암호화 키를 저장하지 않는다.
- `compose.yaml`은 `POSTGRES_PASSWORD`, `DATABASE_URL`이 없으면 실패한다.
- `make compose-config`는 `docker compose config --quiet`로 실행해 resolved 환경변수를 로그에 출력하지 않는다.
- 프론트엔드 `VITE_*` 환경변수에는 Secret을 넣지 않는다.
