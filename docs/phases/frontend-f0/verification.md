# Frontend Phase F0 Verification

## Commands Run

```bash
docker compose -f compose.yaml config
```

Result: passed. Docker emitted warnings that `C:\Users\user\.docker\config.json` could not be read because access was denied, but the compose configuration was rendered successfully.

```bash
cd frontend && npm.cmd test
```

Result: passed with elevated filesystem access after the initial sandboxed run failed while esbuild loaded `vite.config.ts`. Vitest ran 1 test file and 1 test.

```bash
cd frontend && npm.cmd run typecheck
```

Result: passed.

```bash
cd frontend && npm.cmd run build
```

Result: passed with elevated filesystem access after the initial sandboxed run failed while esbuild loaded `vite.config.ts`.

```bash
git diff --check
```

Result: passed.

## Review Follow-up Verification

After adding the P1/P2 review follow-ups for state architecture, graph-click race handling, MSW mocks, and responsive breakpoints, these checks were rerun:

```bash
python scripts\check-doc-links.py
git diff --check
```

Result: passed.

After adding the second review follow-ups for ID-only UI store state, `usePolicyNodeSelection`, MSW contract SSOT, and mobile state preservation, these checks were rerun:

```bash
python scripts\check-doc-links.py
git diff --check
```

Result: passed.

After adding the third review follow-ups for type-level UI store guardrails, OpenAPI-generated MSW response types, silent abort/cancel handling, and hidden mobile graph work pausing, these checks were rerun:

```bash
python scripts\check-doc-links.py
git diff --check
```

Result: passed.

After adding the fourth review follow-ups for TypeScript strictness, restricted-import linting expectations, OpenAPI type-sync CI, TanStack Query signal usage, and inactive-panel render skipping, these checks were rerun:

```bash
cd frontend && npm.cmd run typecheck
python scripts\check-doc-links.py
git diff --check
```

Result: passed.

After adding the fifth review follow-ups for OpenAPI snapshot-based CI isolation, precise UI-store lint targeting, MSW Node/browser entry separation, rapid-switch abort integration tests, and mobile shell/body render separation, these checks were rerun:

```bash
cd frontend && npm.cmd run typecheck
python scripts\check-doc-links.py
git diff --check
```

Result: passed.

After adding the sixth review follow-ups for OpenAPI snapshot sync PR workflows, inline suppression controls, CI path filtering/caching, and MSW parallel test isolation, these checks were rerun:

```bash
cd frontend && npm.cmd run typecheck
python scripts\check-doc-links.py
git diff --check
```

Result: passed.

## Additional Attempts

```bash
cd frontend && npm test
cd frontend && npm run typecheck
cd frontend && npm run build
```

Result: failed in PowerShell because script execution policy blocked `npm.ps1`.

```bash
cd frontend && npm.cmd test
cd frontend && npm.cmd run build
```

Result: failed in the sandbox because esbuild could not read an ancestor directory while resolving `vite.config.ts`. Both commands passed with elevated filesystem access.

```bash
cd frontend && npm.cmd install
```

Result: failed in the sandbox because npm could not complete registry download and cleanup/cache writes. The command passed with elevated network and filesystem access.

## Not Run or Not Applicable

```bash
docker compose -f compose.yaml -f compose.dev.yaml config
```

Result: not applicable. `compose.dev.yaml` does not exist in this repository.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend alembic upgrade head
```

Result: not applicable. `compose.dev.yaml`, Alembic configuration, and migrations do not exist yet.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest
```

Result: not applicable. `compose.dev.yaml` does not exist and the backend environment currently uses the existing local test setup.

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check app tests
```

Result: not applicable. `compose.dev.yaml` and Ruff configuration do not exist yet. The current backend package path is `src/app`.
