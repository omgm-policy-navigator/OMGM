# AI Phase A2 Plan

## Goal

Extract only approved user-condition candidates from free-form input without treating ambiguity or conflicts as confirmed facts.

## Scope

- Define the seven allowed fact-key Enum values.
- Build a constrained condition-extraction prompt.
- Validate candidate keys, confidence, ambiguity, and evidence.
- Compute confirmation requirements in backend code.
- Detect conflicts with existing confirmed user facts.
- Add focused tests and update architecture, ownership, and security contracts.

## Completion Criteria

- Unknown condition keys cannot pass the extraction schema.
- Ambiguous or confidence-below-`0.8` candidates require confirmation.
- A changed value for an existing confirmed fact returns a conflict requiring resolution.
- Tests, lint, Compose configuration, and migration verification pass.

## Out of Scope

- HTTP endpoints and conversation orchestration.
- A physical `user_fact` table or candidate persistence.
- Final eligibility calculation.
- Domain-specific canonical value normalization.
- Expanding the allowlist from all policy-seed condition keys.
