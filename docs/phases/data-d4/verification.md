# Analysis Phase D4 Verification

## 검증 명령

```powershell
cd backend
python -m pytest -q --basetemp <workspace-temp> -p no:cacheprovider
```

결과: 통과. 전체 115개 테스트가 통과했다.

```powershell
cd backend
python -m unittest discover -s tests
```

결과: 통과. unittest discovery 기준 97개 테스트가 통과했다.

```powershell
cd backend
ruff check src/app tests
```

결과: 통과.

```powershell
python scripts/check-doc-links.py
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
git diff --check
```

결과: 통과. Docker 사용자 전역 config 접근 경고가 있었지만 Compose 계약 검사는 exit code 0이었다.

```powershell
cd backend
alembic heads
alembic history
```

결과: 통과. 단일 head는 `20260806_0003`이다.

Docker runtime 검증 명령은 실제 실행을 시도했으나 Docker Desktop 엔진이 실행 중이지 않아 `docker_engine` named pipe 연결 전에 종료됐다.

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --build --rm backend alembic upgrade head
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
```

## Migration

D4는 분석 DTO와 CSV Seed만 변경하므로 신규 Alembic migration을 추가하지 않는다. 기존 migration metadata chain은 검증했으며 컨테이너 `upgrade head`는 로컬 Docker 엔진 부재로 실행되지 못했다.

## Troubleshooting

현재까지 재사용 가능한 신규 장애는 확인되지 않았다. Docker 이미지 불일치와 Windows 권한 문제는 기존 [Docker backend image 재빌드](../../troubleshooting/docker-backend-image.md)를 따른다.
