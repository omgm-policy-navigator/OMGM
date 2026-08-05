# Frontend Phase F1 Progress

## Status

Completed on branch `frontend-f1-react-query-ui`.

## Completed Work

- Created the F1 frontend source structure under `frontend/src/app`, `pages`, `features`, `entities`, and `shared`.
- Added TanStack Query and wired a shared `QueryClientProvider`.
- Added a shared API client that uses `fetch`, `credentials: "include"`, and `AbortSignal`.
- Added environment-based Health behavior through `VITE_API_MODE`.
- Added a synthetic mock Health response for local frontend-first execution.
- Added a common `AppShell` layout and a minimal `NavigatorPage`.
- Added ESLint configuration and `npm run lint`.
- Added frontend lint execution to GitHub Actions CI.
- Updated frontend documentation for lint and `VITE_API_MODE`.
- Updated phase verification records.
- Added TypeScript and Vite `@/*` path aliases for the FSD source structure.
- Added ESLint FSD layer-direction rules for `shared`, `entities`, `features`, and `pages`.
- Added FSD public API `index.ts` entry points and lint guardrails that block deep imports into `pages`, `features`, and `entities` slices.
- Added runtime fail-fast validation for required `VITE_*` environment variables.
- Ensured the environment validation module is the first import evaluated from `main.tsx`.
- Added explicit API client error type and mutation/query default options.
- Replaced the manual Vite alias with `vite-tsconfig-paths` so Vite and Vitest consume `tsconfig.json` path aliases consistently.
- Configured Vitest env values so tests validate the app without depending on a live backend or local `.env`.

## Deferred

- MSW setup is deferred because F1 only needs a mock Health response and not a full API mocking layer.
- OpenAPI type generation is deferred until the backend exposes the relevant OpenAPI contract for frontend DTO generation.
- Chatbot, policy graph, policy detail, session lifecycle UI, and cross-panel state store are deferred to later frontend phases.
- Troubleshooting documentation was not added because no reusable runtime issue was diagnosed and resolved in this phase.
