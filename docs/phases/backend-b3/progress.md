# Backend Phase B3 Progress

## Status

Implemented on branch `backend-b3-anonymous-session`.

## Completed Work

- Added `app/modules/sessions` with API DTOs, cookie helpers, token hashing, repository functions, and service logic.
- Added server-generated anonymous session tokens transported only in the `anonymous_session` HttpOnly cookie.
- Stored only SHA-256 token hashes in `anonymous_session`; raw tokens are never returned in JSON.
- Added absolute session expiry of 24 hours and idle expiry of 60 minutes by default.
- Added Origin validation for cookie-authenticated unsafe methods.
- Added `user_fact` upsert and listing scoped by the resolved session database identity.
- Added session deletion with cookie clearing and database cascade delete for facts.
- Added expired-session cleanup repository/service function and invoked cleanup during session creation.
- Added B3 tests for cookie-only session identity, ignored client-supplied JSON session IDs, expired-session rejection, fact scoping, cleanup delegation, and cascade relationship.

## Deferred

- Periodic background cleanup scheduling.
- Fact conflict detection and versioning.
- Conversation-driven question collection.
- Eligibility evaluation using stored facts.
