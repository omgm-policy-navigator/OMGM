# AI Phase A2 Progress

## Status

Implemented on branch `phase-a2-user-condition-extraction`.

## Completed Work

- Added `app.modules.user_facts` as the A2 analysis boundary.
- Added the seven-key `AllowedFactKey` allowlist.
- Added a prompt that prohibits inference and requires JSON-only output.
- Added strict validation for keys, values, confidence, ambiguity, evidence, extra fields, and duplicate keys.
- Added backend-owned confirmation rules with a `0.8` confidence threshold.
- Added confirmed-fact conflict detection and resolution-required output.
- Added focused tests for prompt constraints, invalid keys, ambiguity, confidence, and conflicts.
- Updated AI, backend, module-boundary, data-ownership, and security documentation.

## Deferred

- API exposure and conversation orchestration.
- User-fact persistence and migrations.
- Runtime-specific extraction invocation and retry orchestration.
- Domain-specific canonical value normalization.
