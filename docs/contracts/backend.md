# Backend Contract

## Phase 1 Runtime Contract

- Python version: 3.11
- Package manager: `uv`
- Project file: `backend/pyproject.toml`
- Lockfile: `backend/uv.lock`
- ASGI app: `app.main:app`
- Local run command: `cd backend && uv run uvicorn app.main:app --reload`
- Docker run command: `docker compose up`
- Swagger URL: `http://localhost:8000/`
- Health endpoint: `GET /health`

## Environment Variables

| Name | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APP_ENV` | No | `local` | Runtime environment label. |
| `LOG_LEVEL` | No | `INFO` | Backend log level. |
| `BACKEND_HOST` | No | `0.0.0.0` | Uvicorn bind host. |
| `BACKEND_PORT` | No | `8000` | Uvicorn bind port. |
| `DATABASE_URL` | Yes in Docker | local PostgreSQL URL | PostgreSQL async SQLAlchemy URL. |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | Frontend origin allowlist. |

## Current API

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "omgm-backend",
  "environment": "local"
}
```

No business API, authentication, repository, ORM model, or migration contract is introduced in Phase 1.
