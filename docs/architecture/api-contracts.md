# Backend API Contracts

## Contract Status

This document is the Phase B0 backend API draft. Only `GET /health` is implemented. Other endpoints define mockable contracts so frontend, backend, and data-pipeline work can proceed without sharing internal entities.

Base URL for local development: `http://localhost:8000`.

## Common Rules

- Request and response bodies use JSON unless the endpoint is explicitly SSE.
- API response schemas are DTOs and must not be SQLAlchemy entities.
- Unknown values are omitted or returned as `null` with an explicit status. They are not converted to `false` or `0`.
- Dates and timestamps use ISO 8601 strings.
- Policy and evaluation responses include policy version where eligibility depends on policy data.
- Sensitive user facts are minimized in responses and must not be logged.

## Error Response

All handled application errors return this shape:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Requested resource was not found."
  }
}
```

### Error Codes

| Code | HTTP status | Meaning |
| --- | ---: | --- |
| `VALIDATION_ERROR` | 422 | Request body, path, or query parameters failed validation. |
| `CONFIGURATION_ERROR` | 500 | Backend configuration is invalid. |
| `SESSION_NOT_FOUND` | 404 | Anonymous or account session does not exist. |
| `POLICY_NOT_FOUND` | 404 | Requested policy does not exist. |
| `POLICY_UNAVAILABLE` | 503 | Policy data or evidence is not available enough to evaluate. |
| `EVALUATION_NOT_FOUND` | 404 | Requested evaluation does not exist. |
| `CONFLICTED_FACTS` | 409 | New user facts conflict with existing confirmed facts. |
| `INSUFFICIENT_INFORMATION` | 409 | Required facts are missing and eligibility cannot be finalized. |
| `RATE_LIMITED` | 429 | Client exceeded allowed request volume. |
| `INTERNAL_ERROR` | 500 | Unexpected server error with safe public message. |

## Implemented Endpoint

### `GET /health`

Returns backend process health.

Response `200`:

```json
{
  "status": "ok",
  "service": "omgm-backend",
  "environment": "local"
}
```

## Draft Endpoints

### `POST /api/sessions/anonymous`

Creates or refreshes an anonymous session owned by the backend.

Request:

```json
{
  "clientSessionId": "optional-browser-generated-id"
}
```

Response `201`:

```json
{
  "sessionId": "anon_123",
  "expiresAt": "2026-08-05T12:00:00Z"
}
```

### `GET /api/policies`

Lists policy summaries using filters owned by the backend.

Query parameters:

| Name | Required | Meaning |
| --- | --- | --- |
| `region` | no | Administrative region filter. |
| `lifeEvent` | no | User life event such as `engaged` or `newlywed`. |
| `cursor` | no | Pagination cursor. |
| `limit` | no | Page size. |

Response `200`:

```json
{
  "items": [
    {
      "policyId": "policy_123",
      "title": "신혼부부 주거 지원",
      "agency": "서울시",
      "region": "서울",
      "status": "ACTIVE",
      "policyVersion": "2026-08-01"
    }
  ],
  "nextCursor": null
}
```

### `GET /api/policies/{policyId}`

Returns policy detail and source metadata.

Response `200`:

```json
{
  "policyId": "policy_123",
  "title": "신혼부부 주거 지원",
  "agency": "서울시",
  "region": "서울",
  "status": "ACTIVE",
  "policyVersion": "2026-08-01",
  "source": {
    "url": "https://example.go.kr/policy/123",
    "collectedAt": "2026-08-05T00:00:00Z",
    "documentHash": "sha256:..."
  }
}
```

### `POST /api/conversations`

Starts a policy navigation conversation for an anonymous session.

Request:

```json
{
  "sessionId": "anon_123",
  "initialMessage": "서울 신혼부부 전세 지원을 찾고 싶어요"
}
```

Response `201`:

```json
{
  "conversationId": "conv_123",
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

### `POST /api/conversations/{conversationId}/answers`

Stores normalized user facts collected through a conversation.

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
  "factVersion": "facts_v2",
  "conflicts": [],
  "nextQuestions": []
}
```

### `POST /api/evaluations`

Evaluates policies using verified structured rules and current user facts.

Request:

```json
{
  "sessionId": "anon_123",
  "policyIds": ["policy_123"]
}
```

Response `200`:

```json
{
  "items": [
    {
      "evaluationId": "eval_123",
      "policyId": "policy_123",
      "status": "NEEDS_CONFIRMATION",
      "policyVersion": "2026-08-01",
      "factVersion": "facts_v2",
      "coverage": {
        "requiredKnown": 2,
        "requiredTotal": 3
      },
      "satisfied": ["region"],
      "unsatisfied": [],
      "needsConfirmation": ["income"]
    }
  ]
}
```

Allowed evaluation statuses:

- `ELIGIBLE`
- `INELIGIBLE`
- `NEEDS_CONFIRMATION`
- `STALE`
- `CONFLICTED`
- `NOT_EVALUATED`
- `POLICY_UNAVAILABLE`

### `GET /api/evaluations/{evaluationId}`

Returns an evaluation result and evidence references.

Response `200`:

```json
{
  "evaluationId": "eval_123",
  "policyId": "policy_123",
  "status": "NEEDS_CONFIRMATION",
  "policyVersion": "2026-08-01",
  "factVersion": "facts_v2",
  "evidence": [
    {
      "conditionId": "cond_income",
      "sourceUrl": "https://example.go.kr/policy/123",
      "sourceLabel": "소득 기준",
      "documentVersion": "2026-08-01"
    }
  ]
}
```

### `GET /api/policies/{policyId}/graph`

Returns graph projection data for UI rendering.

Response `200`:

```json
{
  "nodes": [
    {
      "id": "policy_123",
      "type": "policy",
      "label": "신혼부부 주거 지원"
    }
  ],
  "edges": []
}
```

### `POST /api/saved-policies`

Saves a policy for an anonymous or authenticated user context.

Request:

```json
{
  "sessionId": "anon_123",
  "policyId": "policy_123"
}
```

Response `201`:

```json
{
  "savedPolicyId": "saved_123",
  "policyId": "policy_123"
}
```

### `GET /api/notifications`

Lists policy and evaluation notifications for the current session or account.

Response `200`:

```json
{
  "items": [
    {
      "notificationId": "notice_123",
      "type": "POLICY_CHANGED",
      "policyId": "policy_123",
      "createdAt": "2026-08-05T00:00:00Z",
      "read": false
    }
  ]
}
```

## Mock Contract Rules

Mocks must preserve the response envelopes, status strings, and null handling defined here. Mock data must be synthetic and must not include real personal data or real application records.
