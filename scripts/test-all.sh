#!/usr/bin/env sh
set -eu

docker compose -f compose.yaml -f compose.dev.yaml config --quiet
docker compose -f compose.yaml -f compose.dev.yaml run --build --rm backend alembic upgrade head
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check src/app tests
docker compose -f compose.yaml -f compose.dev.yaml run --build --rm --no-deps frontend npm test
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend npm run lint
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend npm run typecheck
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend npm run build
