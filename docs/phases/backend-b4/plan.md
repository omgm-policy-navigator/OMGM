# Backend Phase B4 Plan

## Goal

Select the next required question from the user's chosen policy category and existing anonymous-session facts.

## Scope

- Store the selected category on the anonymous session.
- Add MVP question templates by category.
- Rank questions by priority and discriminator score.
- Support parent-child questions through `showCondition`.
- Exclude already answered facts.
- Report required-question completion progress.
- Detect conflicting answers and return a reconfirmation question.

## Out of Scope

- Policy eligibility evaluation.
- Conversation orchestration and natural-language question generation.
- Persisted question-bank administration.
- Marking evaluation records `STALE`; B4 has no evaluation persistence yet.