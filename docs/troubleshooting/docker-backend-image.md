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
