# Backend Phase 1 Port Conflict

## 증상

`docker compose up --build -d postgres backend` 이후 host에서 다음 명령을 실행했을 때 404가 반환됐다.

```bash
curl -i http://127.0.0.1:8000/health
```

backend 컨테이너 로그에는 해당 요청 access log가 남지 않았다.

## 환경

- macOS 로컬 개발 환경
- Docker Compose backend port: `0.0.0.0:8000->8000/tcp`
- 다른 로컬 Python uvicorn 프로세스도 host port 8000을 listen 중

## 확인 명령

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
docker compose port backend 8000
docker compose logs --tail=80 backend
```

## 원인

host port 8000을 다른 로컬 프로젝트의 uvicorn 프로세스가 함께 점유하고 있어 host curl 요청이 기대한 backend 컨테이너로 도달하지 않았다.

## 해결

다른 프로젝트 프로세스를 임의 종료하지 않고, Compose backend 컨테이너 내부에서 직접 health와 Swagger를 검증했다.

```bash
docker compose exec backend python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health'); print(r.status); print(r.read().decode())"
docker compose exec backend python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/'); print(r.status); print(r.headers.get('content-type'))"
```

## 검증

- `/health`: `200`
- Swagger root `/`: `200`, `text/html; charset=utf-8`
