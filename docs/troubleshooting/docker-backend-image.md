# Docker backend image 재빌드

## 증상

의존성이나 Dockerfile 변경 후 아래 명령에서 `alembic: executable file not found`가 발생할 수 있다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
```

## 원인

`docker compose run`이 변경 전 backend 이미지를 재사용하면 현재 `pyproject.toml`에 있는 실행 파일이나 새 데이터 디렉터리가 이미지에 없다.

## 해결

최신 이미지를 명시적으로 빌드해 실행한다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --build --rm backend alembic upgrade head
```

이후 동일 이미지의 테스트와 Lint를 실행해 이미지에 코드·의존성·정책 CSV가 함께 포함됐는지 확인한다.

## Windows 권한 오류 회피

Windows 로컬 실행에서 pytest 임시 폴더 `PermissionError` 또는 Vite/esbuild 상위 경로 접근 오류가 발생하면 저장소 루트에서 Docker 검증을 사용한다.

```powershell
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
docker compose -f compose.yaml -f compose.dev.yaml run --build --rm backend alembic upgrade head
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
docker compose -f compose.yaml -f compose.dev.yaml run --build --rm --no-deps frontend npm test
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend npm run lint
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend npm run typecheck
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend npm run build
```

`--build`가 붙은 첫 실행은 현재 Dockerfile과 lockfile을 이미지에 반영한다. 이후 동일 이미지의 명령은 소스 볼륨 또는 빌드된 이미지 기준으로 실행된다.

## CI에서만 policy seed 테스트가 실패하는 경우

Windows 작업 트리는 CSV를 CRLF로 checkout할 수 있고 GitHub Actions의 Linux 작업 트리는 LF로 checkout한다. 원시 bytes 체크섬은 같은 CSV 내용도 서로 다른 파일로 판단한다.

Policy seed 로더는 체크섬 계산 전에 CRLF를 LF로 정규화한다. `SHA256SUMS`를 갱신할 때도 LF 정규화 bytes를 기준으로 계산해야 하며, 실제 셀 내용 변경은 계속 탐지한다.
