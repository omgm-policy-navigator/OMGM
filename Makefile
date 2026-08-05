SHELL := /bin/sh

.PHONY: help check-env env-check dev dev-logs dev-down setup setup-backend setup-frontend \
	backend-run frontend-run \
	test test-backend test-frontend typecheck-frontend build-frontend \
	docker-up docker-build docker-infra-up docker-down docker-ps docker-logs compose-config \
	health verify clean

help:
	@printf "%s\n" "Available targets:"
	@printf "%s\n" "  dev               Build and run every local service in the background"
	@printf "%s\n" "  dev-logs          Follow logs for every local service"
	@printf "%s\n" "  dev-down          Stop the local development stack"
	@printf "%s\n" "  env-check         Verify local env files are not tracked"
	@printf "%s\n" "  setup             Install backend and frontend dependencies"
	@printf "%s\n" "  backend-run       Run FastAPI backend on port 8000"
	@printf "%s\n" "  frontend-run      Run Vite frontend on port 5173"
	@printf "%s\n" "  test              Run backend and frontend test/typecheck/build"
	@printf "%s\n" "  docker-up         Build and run the full local stack"
	@printf "%s\n" "  docker-infra-up   Run PostgreSQL/pgvector and Ollama only"
	@printf "%s\n" "  docker-down       Stop local Docker Compose stack"
	@printf "%s\n" "  compose-config    Validate Docker Compose configuration without printing secrets"
	@printf "%s\n" "  health            Call backend health check"
	@printf "%s\n" "  verify            Run structure, compose, tests, and markdown link checks"

check-env:
	@test -f .env || (printf "%s\n" "Missing .env. Run: cp .env.example .env"; exit 1)
	@! grep -q "replace-with-local-password" .env || (printf "%s\n" "Replace POSTGRES_PASSWORD and DATABASE_URL placeholders in .env before running containers."; exit 1)
	@! grep -q "local-dev-only-password" .env || (printf "%s\n" "Use a non-shared local POSTGRES_PASSWORD in .env before running containers."; exit 1)

env-check:
	@git check-ignore -q .env
	@git check-ignore -q backend/.venv/
	@git check-ignore -q frontend/node_modules/
	@git check-ignore -q frontend/dist/
	@git check-ignore -q frontend/tsconfig.tsbuildinfo
	@printf "%s\n" "env and local artifacts are ignored"

dev: check-env
	docker compose up --build -d
	$(MAKE) docker-ps

dev-logs:
	docker compose logs -f

dev-down:
	docker compose down

setup: setup-backend setup-frontend

setup-backend:
	cd backend && python3.11 -m venv .venv
	cd backend && . .venv/bin/activate && python -m pip install --upgrade pip
	cd backend && . .venv/bin/activate && python -m pip install -e .

setup-frontend:
	cd frontend && npm install

backend-run:
	cd backend && . .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

frontend-run:
	cd frontend && npm run dev

test: test-backend test-frontend typecheck-frontend build-frontend

test-backend:
	cd backend && . .venv/bin/activate && python -m unittest discover

test-frontend:
	cd frontend && npm test

typecheck-frontend:
	cd frontend && npm run typecheck

build-frontend:
	cd frontend && npm run build

docker-up: check-env
	docker compose up --build

docker-build:
	docker compose build

docker-infra-up: check-env
	docker compose up -d postgres ollama

docker-down:
	docker compose down

docker-ps:
	docker compose ps

docker-logs:
	docker compose logs -f

compose-config:
	docker compose config --quiet

health:
	curl -f http://localhost:8000/health

verify:
	scripts/verify-structure.sh
	$(MAKE) compose-config
	$(MAKE) env-check
	$(MAKE) test
	backend/.venv/bin/python scripts/check-doc-links.py

clean:
	rm -rf frontend/dist frontend/tsconfig.tsbuildinfo
	find backend -type d -name __pycache__ -prune -exec rm -rf {} +
