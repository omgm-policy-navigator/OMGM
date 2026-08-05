# Frontend F0 API Mock Contracts

## Status

This document defines the Frontend Phase F0 mock contract used by `NavigatorPage` and its child components. It does not replace `docs/architecture/api-contracts.md`; backend API DTOs there remain the source contract. Mocks must follow the same envelopes, status strings, cookie rules, and null handling.

Only `GET /health` is implemented today. All other contracts below are mockable draft contracts for frontend state design and tests.

## Common Client Rules

- Requests that depend on the anonymous session use browser cookies with `credentials: "include"`.
- The frontend never reads, stores, logs, or submits the anonymous session ID.
- Unknown user facts are represented as `null` or omitted with explicit status text. They are not converted to `false`, `0`, or an empty string.
- Mock data is synthetic and must not include real personal data, income, asset, address, or application records.
- API response schemas are client DTOs and must not be imported from SQLAlchemy entities.
- Server state is managed through TanStack Query or an equivalent server-state cache. F0 uses TanStack Query terminology for query keys and invalidation rules.
- Cross-panel UI state is managed by a dedicated Zustand store or split React Context. Store selectors must prevent chat input changes from rerendering graph and detail panels.
- Cross-panel UI state stores IDs and view intent only. It must not store copied server payloads such as policy detail, graph projection, conversation responses, evaluations, or evidence arrays.
- Component-local UI state remains inside the owning component unless another panel explicitly depends on it.
- Error mocks use the shared error envelope:

```json
{
  "error": {
    "code": "POLICY_NOT_FOUND",
    "message": "Requested policy does not exist."
  }
}
```

## Screen API Usage

| Screen or component | API contract | Server state owned by backend | UI state owned by frontend |
| --- | --- | --- | --- |
| `NavigatorPage` | `POST /api/session`, `POST /api/conversations`, `POST /api/evaluations` | Anonymous session, conversation id, fact version, evaluation records | Selected category, active policy id, active graph node id, layout mode, pending request markers |
| `CategorySelector` | `GET /api/policies?region&lifeEvent&cursor&limit` | Policy summary list and pagination cursor | Selected category filter, opened selector, client-side highlighted option |
| `ChatPanel` | `POST /api/conversations`, `POST /api/conversations/{conversationId}/answers` | Conversation id, next questions, normalized facts, conflicts | Draft answer text, focused question, local optimistic answer pending state |
| `PolicyGraphPanel` | `GET /api/policies/{policyId}/graph` | Graph projection nodes and edges | View transform, selected node, hovered node, keyboard focus position |
| `PolicyDetailPanel` | `GET /api/policies/{policyId}`, `POST /api/evaluations`, `GET /api/evaluations/{evaluationId}` | Policy detail, source metadata, eligibility result, evidence | Expanded evidence rows, selected detail tab, copied-link feedback |
| `SessionControl` | `POST /api/session`, `POST /api/session/reset`, `DELETE /api/session` | Session creation, reset, deletion, expiry timestamp | Reset confirmation dialog, local disabled state while resetting |

## State Ownership and Cache Keys

| Component | Server state cache key | Cross-panel UI state | Local UI state |
| --- | --- | --- | --- |
| `NavigatorPage` | `["session"]` and mutation coordination only | `selectedCategoryId`, `activePolicyId`, `selectedNodeId`, `activePanel`, latest graph-click token | Route-level composition flags only. |
| `CategorySelector` | `["policies", { "region": region, "lifeEvent": lifeEvent, "cursor": cursor }]` | Writes `selectedCategoryId` | Opened selector and keyboard highlight. |
| `ChatPanel` | `["conversation", conversationId]`, answer mutation by `conversationId` | Reads `activePolicyId`, `selectedNodeId`, `activePanel` | Draft message, focused question id, typing indicator, submit pending marker. |
| `PolicyGraphPanel` | `["policyGraph", activePolicyId]` | Reads/writes `selectedNodeId` | `hoveredNodeId`, `zoomLevel`, pan offset, keyboard focus position. |
| `PolicyDetailPanel` | `["policy", activePolicyId]`, `["evaluation", evaluationId]` | Reads `activePolicyId`, `selectedNodeId`, highlighted evidence id | Expanded evidence rows, selected detail tab, copied-link feedback. |
| `SessionControl` | Session reset/delete mutations | Clears `selectedNodeId`, `activePolicyId`, and `activePanel` after successful reset/delete | Confirmation dialog and button pending marker. |

Query invalidation rules:

- Selecting a new policy enables `["policy", activePolicyId]` and `["policyGraph", activePolicyId]`.
- Submitting answers invalidates `["conversation", conversationId]` and current evaluation queries.
- Resetting or deleting the session clears session-dependent query cache entries and cross-panel selections.
- Graph hover, zoom, draft input, and copied-link feedback never invalidate server-state queries.

Required lookup pattern:

```ts
const activePolicyId = useNavigatorUiStore((state) => state.activePolicyId);
const policyQuery = useQuery({
  queryKey: ["policy", activePolicyId],
  enabled: activePolicyId !== null,
  queryFn: ({ signal }) => fetchPolicy(activePolicyId, { signal }),
});
```

The UI store must contain `activePolicyId`, not `policyQuery.data`. Components derive the displayed server data from the server-state cache.

### UI Store Type Guardrail

The cross-panel UI store type must be constrained to primitive identifiers and pure UI flags. It must not import backend DTOs or generated API response types.

```ts
type ActivePanel = "chat" | "graph" | "detail";

interface NavigatorUiStore {
  selectedCategoryId: string | null;
  activePolicyId: string | null;
  selectedNodeId: string | null;
  highlightedEvidenceId: string | null;
  activePanel: ActivePanel;
  graphClickToken: number;
  isResetDialogOpen: boolean;
  actions: {
    selectNode: (nodeId: string | null, policyId: string | null) => void;
    setActivePanel: (panel: ActivePanel) => void;
    setResetDialogOpen: (open: boolean) => void;
  };
}

// Not allowed in NavigatorUiStore:
// selectedNodeDetail: PolicyDetailResponse;
// graph: PolicyGraphResponse;
// evaluation: EvaluationResponse;
// evidence: EvidenceResponse[];
```

Frontend implementation review must reject UI store additions whose type is an API response DTO, generated OpenAPI response type, graph node array, policy detail object, conversation response, evaluation result, or evidence collection.

This rule must be enforced by compiler and linter configuration when implementation begins:

- `frontend/tsconfig.json` keeps `strict`, `noImplicitAny`, and `strictNullChecks` enabled.
- Store files must not declare fields as generated API response objects or DTO response objects.
- ID-only type extraction from DTOs is allowed when it narrows to primitive identifiers, such as `PolicyDetailResponse["policyId"]`.
- React component files must not import low-level HTTP clients directly; components use feature hooks.
- ESLint `no-restricted-imports` may handle direct HTTP imports in components, but UI store DTO checks should use a custom AST rule or equivalent typed lint rule so type-only ID utility imports are not blocked unnecessarily.
- Critical guardrails must fail on inline suppression. Dedicated guardrail lint jobs should use `--no-inline-config` or scan affected files for `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, and `as any`. Exceptions must be named allowlist entries reviewed in config, not inline comments.

## MSW Mock Standard

Frontend implementation phases must use MSW for API mocking rather than plain JSON-only fixtures. The handler set must live in a frontend-owned mock boundary such as `frontend/src/mocks/handlers.ts`.

Required handler groups:

- Success handlers for each endpoint used by F0 screens.
- Loading or delayed handlers for session, policy list, graph, conversation answer, and evaluation requests.
- Network error handlers for recoverable client states.
- Empty response handlers for no policy list results and empty graph nodes.
- 4xx and 5xx handlers that return the shared error envelope.

Mock response variants must be selected by test setup or scenario configuration, not by changing production API client code.

### Contract SSOT and Type Safety

The source of truth for mock schema shape is `docs/architecture/api-contracts.md` until the backend publishes OpenAPI JSON/YAML. After OpenAPI is available, generated client DTO types become the preferred source.

MSW handlers must return values typed with explicit TypeScript interfaces or generated DTO types. Each handler response should satisfy the same request and response shape as the backend contract. A frontend implementation PR that changes mock response fields must include one of these:

- A matching change to `docs/architecture/api-contracts.md`.
- A regeneration from the backend OpenAPI contract.
- A note proving the changed field is frontend-only test data and not part of the API response.

After OpenAPI exists, CI must generate or verify TypeScript API types before frontend tests run. MSW handlers should type responses with generated path response types.

```ts
import { http, HttpResponse } from "msw";
import type { paths } from "../generated/api-types";

type PolicyDetailResponse =
  paths["/api/policies/{policyId}"]["get"]["responses"]["200"]["content"]["application/json"];

export const handlers = [
  http.get("/api/policies/:policyId", () => {
    const body: PolicyDetailResponse = {
      policyId: "policy_mock_housing_001",
      title: "신혼부부 주거 지원",
      agency: "서울시",
      region: "서울",
      status: "ACTIVE",
      policyVersionId: "policy_version_mock_001",
      source: {
        url: "https://example.go.kr/policy/mock-housing-001",
        collectedAt: "2026-08-05T00:00:00Z",
        documentHash: "sha256:mock",
      },
    };

    return HttpResponse.json<PolicyDetailResponse>(body);
  }),
];
```

Before OpenAPI exists, the same handler must use an explicit local `PolicyDetailResponse` interface copied from `docs/architecture/api-contracts.md`, and the PR verification notes must state that OpenAPI generation was not yet applicable.

CI/CD guardrail once OpenAPI exists:

- Generate `frontend/src/generated/api.schema.d.ts` from a committed OpenAPI snapshot using `openapi-typescript` or an equivalent tool.
- Fail if generated output differs from the committed file.
- Run frontend typecheck after generation so MSW handler drift fails fast.
- Treat manual MSW response changes without regenerated types as incomplete.
- Keep live backend OpenAPI fetching out of ordinary frontend PR CI. Refreshing the committed OpenAPI snapshot from a running backend, remote artifact, scheduled job, or manual sync workflow is separate so backend network availability does not block UI-only PRs.
- Add a scheduled or manually dispatched contract-sync workflow that fetches the latest backend OpenAPI, compares it with the committed snapshot, and opens an update PR when drift is detected. The update PR should include the snapshot, generated API types, and any mock updates needed for typecheck.
- Use path filtering so docs-only PRs do not pay for heavy frontend CI unless they change API contract snapshots or frontend guardrail docs that the PR explicitly wants to validate.
- Cache npm dependencies by `frontend/package-lock.json`.

## MSW Environment Boundaries

MSW must have separate Node and browser entry points:

- `frontend/src/mocks/handlers.ts`: shared handler definitions only.
- `frontend/src/mocks/server.ts`: Node/Vitest entry using `setupServer`.
- `frontend/src/mocks/browser.ts`: local browser development entry using `setupWorker`.

Vitest setup must own the Node server lifecycle:

```ts
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Browser development should start `worker.start()` only from the app's development bootstrap path. Tests must not import `browser.ts`, and production builds must not start MSW.

Parallel test guardrails:

- `server.listen`, `server.resetHandlers`, and `server.close` run from the Vitest setup file loaded in each test environment.
- Tests may override handlers with `server.use`, but must rely on `afterEach(server.resetHandlers)` to remove overrides.
- Shared `handlers` arrays are immutable during tests.
- If Vitest uses worker threads or forks, each worker must create its own MSW server instance through the setup file.
- If a specific network-heavy suite cannot be isolated, only that suite may opt into serial execution; global serial execution is not the default.

## Mock Payloads

### Start session

`POST /api/session`

Response `201` or `200`:

```json
{
  "expiresAt": "2026-08-06T12:00:00Z"
}
```

### Start conversation

`POST /api/conversations`

Request:

```json
{
  "initialMessage": "신혼부부 주거 지원을 찾고 싶어요"
}
```

Response `201`:

```json
{
  "conversationId": "conv_mock_001",
  "nextQuestions": [
    {
      "questionId": "q_region",
      "factKey": "region",
      "prompt": "거주 지역을 확인해 주세요.",
      "answerType": "single_select",
      "required": true,
      "options": ["서울", "경기", "인천"]
    }
  ]
}
```

### Submit answers

`POST /api/conversations/{conversationId}/answers`

Request:

```json
{
  "answers": [
    {
      "questionId": "q_region",
      "factKey": "region",
      "value": "서울",
      "confirmed": true
    }
  ]
}
```

Response `200`:

```json
{
  "factVersion": "facts_mock_v2",
  "conflicts": [],
  "nextQuestions": []
}
```

Conflict mock:

```json
{
  "factVersion": "facts_mock_v3",
  "conflicts": [
    {
      "factKey": "region",
      "previousValue": "경기",
      "newValue": "서울",
      "resolutionRequired": true
    }
  ],
  "nextQuestions": [
    {
      "questionId": "q_region_confirm",
      "factKey": "region",
      "prompt": "이전 답변과 달라졌어요. 현재 거주 지역은 서울이 맞나요?",
      "answerType": "boolean",
      "required": true,
      "options": null
    }
  ]
}
```

### List policies

`GET /api/policies?region=서울&lifeEvent=newlywed&limit=20`

Response `200`:

```json
{
  "items": [
    {
      "policyId": "policy_mock_housing_001",
      "title": "신혼부부 주거 지원",
      "agency": "서울시",
      "region": "서울",
      "status": "ACTIVE",
      "policyVersionId": "policy_version_mock_001"
    }
  ],
  "nextCursor": null
}
```

### Policy detail

`GET /api/policies/{policyId}`

Response `200`:

```json
{
  "policyId": "policy_mock_housing_001",
  "title": "신혼부부 주거 지원",
  "agency": "서울시",
  "region": "서울",
  "status": "ACTIVE",
  "policyVersionId": "policy_version_mock_001",
  "source": {
    "url": "https://example.go.kr/policy/mock-housing-001",
    "collectedAt": "2026-08-05T00:00:00Z",
    "documentHash": "sha256:mock"
  }
}
```

### Policy graph

`GET /api/policies/{policyId}/graph`

Response `200`:

```json
{
  "nodes": [
    {
      "id": "policy_mock_housing_001",
      "type": "policy",
      "label": "신혼부부 주거 지원"
    },
    {
      "id": "condition_region_seoul",
      "type": "condition",
      "label": "서울 거주"
    },
    {
      "id": "question_region",
      "type": "question",
      "label": "거주 지역 확인"
    }
  ],
  "edges": [
    {
      "id": "edge_policy_condition_region",
      "source": "policy_mock_housing_001",
      "target": "condition_region_seoul",
      "type": "requires"
    },
    {
      "id": "edge_condition_question_region",
      "source": "condition_region_seoul",
      "target": "question_region",
      "type": "clarified_by"
    }
  ]
}
```

Allowed node types for F0 mocks:

- `policy`
- `condition`
- `question`
- `evidence`

Allowed edge types for F0 mocks:

- `requires`
- `explained_by`
- `clarified_by`

### Create evaluation

`POST /api/evaluations`

Headers:

```http
Idempotency-Key: <opaque-client-generated-key>
```

Request:

```json
{
  "policyIds": ["policy_mock_housing_001"]
}
```

Response `200`:

```json
{
  "items": [
    {
      "evaluationId": "eval_mock_001",
      "policyId": "policy_mock_housing_001",
      "eligibilityStatus": "NEEDS_CONFIRMATION",
      "evaluationState": "ACTIVE",
      "policyVersionId": "policy_version_mock_001",
      "factVersion": "facts_mock_v2",
      "coverage": {
        "requiredKnown": 1,
        "requiredTotal": 3
      },
      "satisfied": ["region"],
      "unsatisfied": [],
      "needsConfirmation": ["HOUSEHOLD_INCOME_RANGE", "HOUSING_OWNERSHIP"],
      "nextQuestions": ["q_household_income_range", "q_housing_ownership"]
    }
  ]
}
```

### Evaluation detail

`GET /api/evaluations/{evaluationId}`

Response `200`:

```json
{
  "evaluationId": "eval_mock_001",
  "policyId": "policy_mock_housing_001",
  "eligibilityStatus": "NEEDS_CONFIRMATION",
  "evaluationState": "ACTIVE",
  "policyVersionId": "policy_version_mock_001",
  "factVersion": "facts_mock_v2",
  "evidence": [
    {
      "conditionId": "condition_region_seoul",
      "sourceUrl": "https://example.go.kr/policy/mock-housing-001",
      "sourceLabel": "거주 지역 기준",
      "policyVersionId": "policy_version_mock_001"
    }
  ]
}
```

## Loading, Error, and Empty States

| Area | Loading | Error | Empty |
| --- | --- | --- | --- |
| Session | Disable session controls and show neutral progress text. | Show recoverable message and retry action. Do not expose cookie or session details. | No explicit empty state; session is created before interaction. |
| Category policies | Keep selected category visible and show list skeleton. | Preserve previous successful list if available and show retry. | Explain that no mock policies match the selected category; do not imply ineligibility. |
| Chat | Disable submit for the active answer only. | Keep draft answer and show safe error message. | Show starter prompt when no conversation exists. |
| Graph | Keep last graph visible if it belongs to the active policy; otherwise show skeleton. | Show graph-specific retry without clearing policy detail. | Show empty graph message only when API returns zero nodes. |
| Policy detail | Keep selected policy id visible and show detail skeleton. | Show safe error message and link back to policy list. | Show placeholder when no policy is selected. |
| Evaluation | Mark evaluation panel as pending and keep previous result labeled with its `evaluationState`. | Show retry and avoid manufacturing eligibility status. | Show `NOT_EVALUATED` until the user selects a policy or submits required answers. |

## Graph Node Click Conversation Flow

1. User selects a policy from `CategorySelector`.
2. `NavigatorPage` loads `GET /api/policies/{policyId}` and `GET /api/policies/{policyId}/graph`.
3. User clicks a graph node in `PolicyGraphPanel`.
4. For a `policy` node, `NavigatorPage` sets `activePolicyId`, opens `PolicyDetailPanel`, and does not create a chat answer.
5. For a `condition` node with known evidence, `PolicyDetailPanel` highlights the matching condition and evidence reference.
6. For a `condition` node with missing facts, `ChatPanel` focuses the related next question. If no conversation exists, `NavigatorPage` first calls `POST /api/conversations` with a synthetic user-visible initial message based on the selected policy title.
7. For a `question` node, `ChatPanel` moves focus to the matching input, preserving any draft text.
8. Submitting the answer calls `POST /api/conversations/{conversationId}/answers`.
9. After a successful answer response, `NavigatorPage` refreshes evaluation by calling `POST /api/evaluations` with a new `Idempotency-Key`.
10. If the answer response includes conflicts, `PolicyDetailPanel` marks impacted evaluations as `CONFLICTED` until the user resolves the conflict.

### Async Sequence and Race Handling

Each graph node click creates a new `graphClickToken` in cross-panel UI state. Any previous in-flight orchestration for another node is cancelled or ignored.

| Step | Async work | Required stale-response behavior |
| --- | --- | --- |
| Select node | Write `selectedNodeId` and `graphClickToken`. | Supersedes prior node selections immediately. |
| Fetch policy detail or graph-dependent data | Use current `activePolicyId` and selected-node token. | Abort previous fetch with `AbortController` where supported. |
| Create conversation for missing facts | Call `POST /api/conversations` only if the latest selected node still needs a chat question. | Ignore response if the token is stale. |
| Focus chat question or evidence | Update `activePanel`, focused question, and highlighted evidence. | Apply only when `selectedNodeId` still matches the original click. |
| Submit answer and refresh evaluation | Run answer mutation, then evaluation mutation with a new `Idempotency-Key`. | Invalidate only current session/policy evaluation state. |

Implementation phases must pass an `AbortSignal` through fetch-backed API clients. If the selected node changes, pending detail, graph-click, and conversation bootstrap requests should be aborted. If a library cannot cancel a request, completion handlers must compare `graphClickToken` before writing UI state.

When TanStack Query owns a request, query cancellation uses the built-in `queryFn` signal. Do not wrap a query-owned fetch in a second manually-created `AbortController`.

```ts
useQuery({
  queryKey: ["policy", selectedNodeId],
  queryFn: ({ signal }) => fetchPolicyDetail(selectedNodeId, { signal }),
  enabled: selectedNodeId !== null,
});
```

MSW integration tests should cover rapid switching. At minimum, one test should simulate selecting node A and immediately selecting node B, then verify stale node A response is aborted or ignored and no user-facing error is displayed.

Standard hook boundary:

- `usePolicyNodeSelection` owns `AbortController` lifecycle for rapid graph node switching.
- UI store actions write only `selectedNodeId`, `activePolicyId`, `activePanel`, highlighted IDs, and a monotonic `graphClickToken`.
- API client functions accept `{ signal?: AbortSignal }`.
- Components must not start independent graph-click side effects that bypass this hook.
- Canceled node-selection requests are silent control flow and must not display error UI.

Minimal implementation shape:

```ts
function isAbortLikeError(error: unknown) {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (typeof error === "object" &&
      error !== null &&
      "name" in error &&
      (error as { name?: string }).name === "CanceledError")
  );
}

function usePolicyNodeSelection() {
  const controllerRef = useRef<AbortController | null>(null);
  const tokenRef = useRef(0);

  return useCallback(async (nodeId: string, policyId: string) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const token = tokenRef.current + 1;
    tokenRef.current = token;

    try {
      setSelectedNode({ nodeId, policyId, graphClickToken: token });
      await ensureConversationOrEvidenceTarget(nodeId, {
        signal: controller.signal,
      });

      if (controller.signal.aborted || token !== tokenRef.current) {
        return;
      }

      focusCurrentNodeTarget(nodeId);
    } catch (error) {
      if (controller.signal.aborted || isAbortLikeError(error)) {
        return;
      }

      throw error;
    }
  }, []);
}
```

## Accessibility and Responsive Criteria

- `NavigatorPage` exposes one main landmark and each panel has an accessible name.
- `CategorySelector` uses buttons or radio controls for mutually exclusive categories.
- `ChatPanel` keeps input labels programmatically associated and announces new questions through an `aria-live="polite"` region.
- `PolicyGraphPanel` supports keyboard navigation across nodes and exposes selected node text outside the canvas or SVG.
- `PolicyDetailPanel` keeps source links keyboard reachable and labels external links.
- `SessionControl` reset/delete actions require explicit confirmation and return focus to the triggering control.
- At widths below `768px`, mobile uses tab or drawer navigation with one primary work panel visible at a time. Priority is `CategorySelector`, `ChatPanel`, `PolicyGraphPanel`, `PolicyDetailPanel`, then `SessionControl`.
- From `768px` to `1199px`, tablet uses a two-pane split layout where chat and graph remain primary and detail appears as a drawer or secondary panel.
- At `1200px` and above, desktop uses a three-column or pinned split-panel layout where graph, chat, and selected policy detail can be visible together.
- No horizontal scrolling is required for Korean policy names; long labels wrap or truncate with full text available through accessible text.
- Mobile tab or drawer switching preserves draft chat input, graph zoom, graph pan, and scroll position. Prefer hiding inactive panels with CSS while removing them from keyboard and screen-reader navigation, or lift only the volatile local state that must survive an unavoidable unmount.
- Hidden mobile panels must pause expensive work. A graph rendered in canvas or SVG must stop `requestAnimationFrame`, physics simulation ticks, resize observers that trigger layout work, or heavy redraw timers while the graph tab/drawer is inactive. Paused work resumes only when the panel is visible again.
- Hidden mobile panels must avoid expensive rerender work. Keep persisted UI state, but use `React.memo`, narrow store selectors, query `enabled` flags, and an `isActivePanel` prop so inactive panels skip graph layout mapping, parsing, canvas redraw, virtual-list measurement, and other heavy derived computations.
- If display hiding keeps too much work alive, split the panel into a lightweight mounted shell that preserves state and a heavy body that mounts, subscribes, animates, or computes only while active.
