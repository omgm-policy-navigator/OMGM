# AI Contracts

## Phase A0 Goal

AI Phase A0 defines what the LLM may do, what it must not do, and the output contract backend code and mocks must preserve.

## Allowed AI Responsibilities

- Extract candidate policy conditions from natural language or source text for later review.
- Explain administrative terms in plain language.
- Summarize Rule Engine results without changing the result.
- Answer from RAG evidence already retrieved for policies selected by structured metadata and the Rule Engine.

## Forbidden AI Responsibilities

- Decide final eligibility or final application status.
- Execute SQL or choose database queries dynamically.
- Modify policy rules.
- Perform official policy applications or submissions.
- Generate policy facts without cited source evidence.

## Responsibility Boundary

Rule Engine owns deterministic eligibility calculation from structured policy rules and normalized user facts.

RAG owns retrieval of approved source evidence for policies already selected or evaluated by structured metadata and the Rule Engine.

LLM owns language transformation only: condition candidate extraction, administrative term explanation, Rule result summarization, and evidence-grounded answer drafting.

The LLM output is never the source of truth for `eligibilityStatus`, `evaluationState`, policy rules, SQL, or official application actions.

## Output Schema

The backend schema is `app.llm.AIOutput`. JSON responses and mocks use this shape:

```json
{
  "answer": "",
  "resultStatus": "ANSWERED",
  "matchedConditions": [],
  "missingConditions": [],
  "citations": [],
  "nextQuestion": null
}
```

Allowed `resultStatus` values:

- `ANSWERED`: Answer was produced within the allowed AI role.
- `NEEDS_CONFIRMATION`: More user information is needed before a useful explanation can be produced.
- `INSUFFICIENT_EVIDENCE`: RAG evidence is missing or insufficient, so no policy fact is asserted.
- `LLM_UNAVAILABLE`: LLM call failed, timed out, or was skipped.
- `SAFETY_BLOCKED`: The requested response would violate an AI prohibition or safety rule.

`matchedConditions` and `missingConditions` are references to condition IDs and labels. They are not final eligibility decisions.

`citations` must reference approved sources with `sourceId`, `title`, `url`, and `policyVersionId`. Excerpts are optional and must not include sensitive user facts.

`nextQuestion` is either `null` or one follow-up question with `questionId`, `prompt`, and `factKey`.

## Fallback Contract

When the LLM is unavailable, the backend returns:

```json
{
  "answer": "현재 AI 설명을 생성할 수 없습니다. 구조화된 판정 결과와 근거를 확인해 주세요.",
  "resultStatus": "LLM_UNAVAILABLE",
  "matchedConditions": [],
  "missingConditions": [],
  "citations": [],
  "nextQuestion": null
}
```

When RAG evidence is insufficient, the backend returns `INSUFFICIENT_EVIDENCE`, leaves `citations` empty, and does not invent policy facts.

When required user facts are missing, the backend returns `NEEDS_CONFIRMATION` with `missingConditions` and, when available, `nextQuestion`.

Fallback responses must not convert unknown data to false or zero, must not create arbitrary policy facts, and must not invent an eligibility-like result.
