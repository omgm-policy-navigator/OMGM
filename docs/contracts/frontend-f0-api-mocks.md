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

## Accessibility and Responsive Criteria

- `NavigatorPage` exposes one main landmark and each panel has an accessible name.
- `CategorySelector` uses buttons or radio controls for mutually exclusive categories.
- `ChatPanel` keeps input labels programmatically associated and announces new questions through an `aria-live="polite"` region.
- `PolicyGraphPanel` supports keyboard navigation across nodes and exposes selected node text outside the canvas or SVG.
- `PolicyDetailPanel` keeps source links keyboard reachable and labels external links.
- `SessionControl` reset/delete actions require explicit confirmation and return focus to the triggering control.
- At widths below `768px`, panels stack in this order: `CategorySelector`, `ChatPanel`, `PolicyGraphPanel`, `PolicyDetailPanel`, `SessionControl`.
- At widths `768px` and above, chat and graph may sit side by side, with detail shown as a secondary panel.
- No horizontal scrolling is required for Korean policy names; long labels wrap or truncate with full text available through accessible text.
