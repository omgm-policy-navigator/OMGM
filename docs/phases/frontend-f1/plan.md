# Frontend Phase F1 Plan

## Goal

Run the React, Vite, and TypeScript frontend project with a minimal app shell, API client boundary, TanStack Query, tests, linting, and frontend CI.

## Scope

- Keep the existing Vite + React + TypeScript project and align it with the F1 source structure.
- Add TanStack Query as the server-state boundary.
- Add a frontend API client boundary.
- Display a synthetic mock Health response without requiring the backend server.
- Add a common layout shell.
- Add ESLint and wire it into frontend CI.
- Enforce FSD public API imports and one-way layer dependencies with ESLint.
- Keep environment variables separated through `VITE_*` values.

## Source Structure

```text
frontend/src/
├── app/
├── pages/
├── features/
├── entities/
└── shared/
```

## Implementation Notes

- `app/` owns app composition and providers.
- `pages/` owns route-level screens.
- `features/` owns vertical user-facing units such as Health status.
- `entities/` owns frontend model types that are not backend entities.
- `shared/` owns reusable API, config, and UI primitives.
- `VITE_API_MODE=mock` returns a synthetic Health response.
- `VITE_API_MODE=live` calls the backend `GET /health` endpoint through the API client.
- FSD slice imports for `pages`, `features`, and `entities` must go through each slice `index.ts`.
- Each FSD slice `index.ts` must explicitly re-export only the external interface, component, hook, and type surface intended for other slices. Do not use broad `export *` as the default pattern.
- The allowed layer direction is `app -> pages -> widgets -> features -> entities -> shared`; lower layers must not import higher layers.
- `shared/` must stay domain-free. It may contain UI primitives, global config, common fetchers, pure utilities, and global types only. Policy, chat, graph, eligibility, or user-fact logic belongs in `entities` or `features`.
- Environment validation must be imported as the first side effect in `main.tsx` before app composition is loaded.
- Vite and Vitest use `vite-tsconfig-paths` so `@/*` aliases are derived from `tsconfig.json`.
- Slice public APIs should use named exports to preserve readable imports and tree-shaking. The frontend package declares `"sideEffects": false` because modules are expected to be side-effect free except explicit entry side effects such as `main.tsx` and environment validation.
- Component tests and future Storybook stories must not mock whole FSD slice public APIs such as `vi.mock("@/entities/policy")`. Prefer data-level mocks through API/MSW handlers so unrelated exports in the same public API remain intact.

## Completion Criteria

- Frontend development server starts.
- Mock Health response is displayed.
- Lint, test, typecheck, and build pass.
- Frontend CI runs lint, test, typecheck, and build.
- Environment variables remain under `VITE_*` and contain no secrets.
- Deep imports such as `@/features/health/api/useHealthQuery` from outside the slice fail lint.
- Slice `index.ts` files expose the public contract with named re-exports only.
- Shared code contains no domain-specific policy/chat/graph logic.

## Out of Scope

- Implementing the F0 chatbot, graph, detail, and session-control behavior.
- Introducing production API mocks, MSW handlers, OpenAPI generation, or custom lint rules.
- Backend endpoint or database changes.
- Persisting user state.
