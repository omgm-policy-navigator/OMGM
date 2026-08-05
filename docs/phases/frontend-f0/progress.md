# Frontend Phase F0 Progress

## Status

Completed on branch `frontend-f0-screen-state-contracts`.

## Completed Work

- Confirmed the current repository is on `main` before creating the F0 branch.
- Confirmed `docs/contracts` and `docs/troubleshooting` did not exist before this phase.
- Confirmed no SQLAlchemy models or Alembic migrations exist yet.
- Confirmed the current backend tests are organized under `backend/tests/unit`, `backend/tests/integration`, and `backend/tests/fixtures`.
- Defined the `NavigatorPage` screen structure and child component responsibilities.
- Separated server state from frontend UI state for the chatbot, graph, detail panel, and session controls.
- Added frontend API mock contracts for session, policy list, policy detail, conversation answers, graph projection, evaluation creation, and evaluation detail.
- Defined loading, error, and empty states for session, category policy list, chat, graph, policy detail, and evaluation areas.
- Defined the graph node click flow into policy detail, evidence highlighting, and chat follow-up questions.
- Recorded accessibility and responsive criteria for the F0 screen structure.
- Added a three-layer state architecture: global/server state, cross-panel UI state, and local UI state.
- Documented TanStack Query-style server state keys and invalidation rules.
- Documented Zustand or split React Context as the cross-panel UI state boundary to avoid `NavigatorPage` becoming a God Component.
- Added async sequencing, stale-response guards, and `AbortController` expectations for graph node click orchestration.
- Added MSW as the frontend API mocking standard with success, loading, network error, empty, and error-envelope handler requirements.
- Expanded responsive layout criteria for mobile, tablet, and desktop breakpoints.
- Added an explicit rule that Zustand or Context UI stores must keep IDs and view intent only, never copied server cache payloads.
- Added `usePolicyNodeSelection` as the standard hook boundary for rapid graph node switching, request abortion, and stale-token checks.
- Clarified that MSW handlers must stay aligned with `docs/architecture/api-contracts.md` or generated OpenAPI DTO types.
- Added mobile tab/drawer state preservation rules for chat drafts, graph zoom/pan, and scroll position.
- Added TypeScript store-interface guardrails that allow only identifiers, primitive UI flags, and actions in cross-panel UI state.
- Added OpenAPI-generated type expectations for MSW handler response type safety once backend OpenAPI is available.
- Added silent handling rules for `AbortError` and `CanceledError` so user-intent cancellation does not show error UI.
- Added mobile hidden-panel resource rules so graph animation and redraw loops pause when inactive.
- Explicitly enabled `noImplicitAny` and `strictNullChecks` in `frontend/tsconfig.json` in addition to existing `strict`.
- Added compiler, restricted import lint, and OpenAPI type-sync CI guardrails for future implementation phases.
- Clarified TanStack Query cancellation must use `queryFn` `signal` instead of duplicate manual controllers.
- Added inactive mounted-panel rerender guardrails using `React.memo`, narrow selectors, query `enabled`, and `isActivePanel`.
- Isolated OpenAPI type-sync CI from live backend availability by requiring committed schema snapshots for ordinary frontend PR checks.
- Refined UI store lint guidance so ID-only utility type extraction is allowed while full response DTO storage is blocked.
- Added MSW `handlers.ts`, `server.ts`, and `browser.ts` environment boundaries and Vitest lifecycle requirements.
- Added an MSW integration-test expectation for rapid node selection cancellation or stale-response ignoring.
- Added a lightweight shell/heavy body pattern for mobile panels that need state preservation without background render cost.
- Added suppression-control guardrails for `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, and `as any`.
- Added separate PR-check and contract-sync workflow responsibilities for OpenAPI snapshot drift.
- Added CI path filtering and npm cache guidance to avoid heavy frontend jobs on unrelated docs-only changes.
- Added MSW parallel test isolation requirements for Vitest worker environments.
- Added contract sync failure alerting requirements for Slack, Discord, email, or GitHub issue fallback.
- Added local Husky/lint-staged pre-commit guardrails for fast staged-file frontend feedback without network coupling.

## Deferred

- Frontend React implementation is deferred to a later phase after the F0 screen and mock contracts are accepted.
- Backend endpoint implementation remains deferred because F0 only defines frontend responsibilities and mock usage.
- SQLAlchemy and Alembic work remains deferred because no database model phase has introduced them yet.
- Troubleshooting documentation was not added because no reusable runtime issue was diagnosed and resolved in this phase.
