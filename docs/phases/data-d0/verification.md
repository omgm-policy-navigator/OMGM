# Data Phase D0 Verification

## Commands Run

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
```

Result: passed. Data Pipeline tests 9개를 실행했으며 Raw schema 검증, 상태 enum, exact-byte SHA-256, 결정적 파일 경로를 포함한다.

```powershell
docker compose -f compose.yaml config --quiet
python scripts\check-doc-links.py
git diff --check
```

Result: passed. Docker는 사용자 전역 config 접근 경고를 출력했지만 Compose 계약 검증은 exit code 0이었다. Markdown link 검사와 whitespace 검사도 통과했다.

## Migration

해당 없음. 현재 저장소에는 SQLAlchemy/Alembic 구성이 없고 D0는 파일 기반 원본 계약을 정의한다.

## Not Applicable

- `compose.dev.yaml`은 저장소에 없다.
- backend Alembic, pytest, Ruff는 현재 backend 환경에 구성되어 있지 않다.

## Attempted but Environment Missing Dependencies

```powershell
cd backend
python -m unittest discover -s tests -v
```

Result: not run successfully. 현재 Windows Python 환경에 backend package와 FastAPI가 설치되어 있지 않아 import 단계에서 종료되었다.

```powershell
cd frontend
npm.cmd test -- --run
npm.cmd run typecheck
npm.cmd run build
```

Result: not run successfully. `frontend/node_modules`가 없어 `vitest`와 `tsc` 실행 파일을 찾지 못했다. D0 변경에는 frontend/backend 실행 코드 변경이 없다.
