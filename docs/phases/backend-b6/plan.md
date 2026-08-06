# Backend Phase B6 Plan

## Goal

Project current-session user facts and policy evaluation results into frontend graph JSON without a separate graph database.

## Scope

- User, category, condition, policy, and action nodes.
- Session fact edges and evaluation-derived condition-to-policy edges.
- Policy relation edges.
- Selected category filtering.
- Selected policy centering with related policies.
- Bounded node counts and truncation signal.
- No persisted graph coordinates or layout state.

## Out of Scope

- Frontend graph rendering.
- Saved graph layouts.
- Graph database adoption.
- Policy evaluation recalculation.