#!/usr/bin/env sh
set -eu

(cd backend && UV_CACHE_DIR=../.uv-cache uv run pytest)
(cd data-pipeline && . .venv/bin/activate && python -m unittest discover)
(cd frontend && npm test && npm run typecheck && npm run build)
