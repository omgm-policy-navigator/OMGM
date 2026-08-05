# Frontend Phase F0 Plan

## Goal

Define the screen responsibilities and state structure so the chatbot and policy graph operate as one user flow.

## Scope

- Define the screen list for `NavigatorPage`.
- Define component ownership boundaries.
- Separate server state from UI state.
- Define frontend API mock contracts.
- Define loading, error, and empty states.
- Define accessibility and responsive criteria.
- Define the conversation flow after a graph node click.

## Screen Structure

```text
NavigatorPage
├── CategorySelector
├── ChatPanel
├── PolicyGraphPanel
├── PolicyDetailPanel
└── SessionControl
```

## Component Responsibilities

| Component | Responsibility | Does not own |
| --- | --- | --- |
| `NavigatorPage` | Orchestrates selected category, selected policy, selected graph node, conversation bootstrap, and evaluation refresh. | Rendering internals for chat, graph, or detail sections. |
| `CategorySelector` | Renders policy category and filter choices and reports filter changes. | Policy evaluation or user fact collection. |
| `ChatPanel` | Renders conversation questions, answer inputs, answer submission, conflicts, and follow-up prompts. | Eligibility calculation or graph projection. |
| `PolicyGraphPanel` | Renders policy, condition, question, and evidence nodes from backend graph projection. | Creating graph relationships or deciding final eligibility. |
| `PolicyDetailPanel` | Renders policy metadata, source metadata, evaluation state, condition status, and evidence references. | Session lifecycle or answer normalization. |
| `SessionControl` | Starts, resets, and ends anonymous browser sessions. | Displaying raw session identifiers. |

## Server State

Server state is fetched from backend contracts and cached or invalidated by the frontend:

- Anonymous session expiry from `POST /api/session`.
- Policy summaries from `GET /api/policies`.
- Policy detail from `GET /api/policies/{policyId}`.
- Policy graph projection from `GET /api/policies/{policyId}/graph`.
- Conversation id, next questions, fact version, and conflicts from conversation endpoints.
- Evaluation summaries and evidence from evaluation endpoints.

## UI State

UI state is local browser state and must not be treated as authoritative domain state:

- Selected category and filter controls.
- Active policy id.
- Active graph node id.
- Hovered and keyboard-focused graph node.
- Expanded evidence rows and selected detail tab.
- Draft chat answer.
- Pending request indicators.
- Retry visibility and reset confirmation dialog.
- Responsive layout mode.

## API Mock Contract

Frontend F0 mock contracts are defined in `docs/contracts/frontend-f0-api-mocks.md`.

The mock contract is intentionally limited to the draft endpoints already described in `docs/architecture/api-contracts.md`. It adds only frontend usage rules, graph node/edge mock shape, loading/error/empty states, and graph-click orchestration. It does not implement backend endpoints or introduce persisted data models.

## Loading, Error, and Empty States

Each screen must define these states before implementation:

- Loading: request-specific pending state, without clearing unrelated successful data.
- Error: safe error envelope display with retry, without exposing raw server details.
- Empty: explicit no-data state that does not imply ineligibility or fabricate eligibility.

Detailed area-level states are recorded in `docs/contracts/frontend-f0-api-mocks.md`.

## Graph Node Click Flow

Graph node clicks are interpreted by node type:

- `policy`: select policy and open detail.
- `condition`: highlight condition and evidence; if facts are missing, focus the related question in chat.
- `question`: focus the matching chat input.
- `evidence`: open or highlight the source reference in policy detail.

When a condition or question requires a conversation and no conversation exists, `NavigatorPage` creates one through `POST /api/conversations` using the selected policy context. Answer submission updates facts and triggers a fresh evaluation request with a new idempotency key.

## Completion Criteria

- Each screen's API usage is defined.
- Loading, error, and empty states are defined.
- Graph node click to chat flow is defined.
- Server state and UI state are explicitly separated.
- F0 status and verification are recorded in this phase folder.

## Out of Scope

- Implementing production graph rendering.
- Implementing backend endpoints beyond existing contracts.
- Adding SQLAlchemy models or Alembic migrations.
- Adding saved policy or notification contracts.
- Introducing WebSocket.
- Persisting frontend UI state beyond the browser session.
