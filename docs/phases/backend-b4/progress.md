# Backend Phase B4 Progress

## Status

Implemented on branch `backend-b4-question-engine`.

## Completed Work

- Added `app/modules/questions` with static MVP question templates and pure question selection logic.
- Added category-specific core questions for housing, loan, cash, childcare, and education.
- Added priority and discriminator-score ordering.
- Added parent-child question handling through `showCondition` and mandatory DAG cycle validation.
- Added selected-category storage on `anonymous_session`.
- Added APIs under `/api/v1/session` for category selection, next question retrieval, answer submission, and progress.
- Stored submitted answers as session-scoped `user_fact` rows through existing B3 storage.
- Added conflict detection for submitted answers that differ from existing confirmed facts, with explicit conflict-resolution response fields.
- Added tests for priority, answered-question exclusion, conditional child questions, completion progress, API category selection, next question, conflict responses, DAG cycle rejection, multi-depth dependent invalidation, and atomic answer/invalidation failure handling.
- Added DFS cascade invalidation that deletes all descendant `user_fact` rows for the current session when a parent answer changes.

## Deferred

- Persisted admin-managed question bank.
- Evaluation `STALE` marking because evaluation persistence is not implemented yet.
- Natural-language question generation.