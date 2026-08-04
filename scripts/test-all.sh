#!/usr/bin/env sh
set -eu

(cd backend && . .venv/bin/activate && python -m unittest discover)
(cd data-pipeline && . .venv/bin/activate && python -m unittest discover)
(cd frontend && npm test && npm run typecheck && npm run build)
