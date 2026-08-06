# Backend Phase B5 Plan

## Goal

Compare anonymous-session user facts with structured policy rules to produce deterministic, reproducible preliminary eligibility results without LLM involvement.

## Scope

- Rule operators: `EQ`, `NE`, `IN`, `NOT_IN`, `LTE`, `GTE`, `BETWEEN`, `BEFORE`, `AFTER`, `EXISTS`.
- Required and optional conditions.
- AND evaluation plus limited OR groups through shared `group_id` in pure Rule Engine inputs.
- Satisfied, unsatisfied, needs-confirmation, and official-confirmation evidence buckets.
- Policy application-window states for ended and future policies.
- Recommendation score ordering.
- `policy_evaluation` persistence scoped to anonymous sessions.
- Session evaluation APIs under `/api/v1/session/evaluations`.
- STALE marking when current-session user facts change.

## Out of Scope

- LLM-based final eligibility decisions.
- Natural-language explanation generation.
- Full admin-managed rule authoring UI.
- Graph projection, saved policies, and notifications.