# Backend Phase B3 Plan

## Goal

Connect anonymous user answers to the same browser session without login, using only a backend-generated HttpOnly cookie identity.

## Scope

- Add `anonymous_session` and `user_fact` persistence tables.
- Add HttpOnly cookie session APIs:
  - `POST /api/session`
  - `GET /api/session`
  - `DELETE /api/session`
  - `GET /api/session/facts`
  - `PUT /api/session/facts/{condition_key}`
- Store and update normalized user facts scoped to the current anonymous session.
- Reject missing or expired sessions.
- Delete facts through database cascade when a session is deleted.
- Add an expired-session cleanup function used on session creation and available for future scheduled cleanup wiring.

## Out of Scope

- Login or account identity.
- Conversation orchestration.
- Policy evaluation against stored facts.
- Saved policies, notifications, or long-term retention.
- Client-visible session IDs or frontend session state integration.
