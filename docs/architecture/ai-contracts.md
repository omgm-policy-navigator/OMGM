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
  "answer": "공고문 기준으로 거주 지역 조건은 충족합니다.",
  "resultStatus": "ANSWERED",
  "matchedConditions": [
    {
      "conditionId": "region",
      "label": "거주 지역",
      "reason": "서울 거주"
    }
  ],
  "missingConditions": [],
  "citations": [
    {
      "sourceId": "doc_1",
      "title": "신혼부부 주거 지원 공고",
      "url": "https://example.go.kr/policy/1",
      "policyVersionId": "policy_version_1",
      "evidenceId": "chunk_1",
      "excerpt": "공고문에서 확인된 근거 문구"
    }
  ],
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

`citations` must reference approved sources with `sourceId`, `title`, `url`, `policyVersionId`, and `evidenceId`. `evidenceId` identifies the approved evidence unit, such as a document chunk. Excerpts are optional, capped, and must not include sensitive user facts.

Citation URLs must be absolute `http` or `https` URLs. `javascript:`, local file paths, localhost URLs, private IP literals, link-local IP literals, loopback IP literals, and internal administrator URLs must not be exposed. The stored URL should be the canonical public source URL, not a redirect URL.

Schema validation rejects non-public IP literals with Python `ipaddress`. Domain names are not resolved during schema validation; any later server-side fetch, link preview, source canonicalization, or citation verification must validate DNS resolution results immediately before fetching.

`nextQuestion` is either `null` or one follow-up question with `questionId`, `prompt`, and `factKey`.

Text and identifier fields are non-empty. `answer` is capped so LLM output cannot grow without bound.

## Status Invariants

`ANSWERED`:

- Requires at least one citation.
- Must not include `missingConditions`.
- Must set `nextQuestion` to `null`.

`NEEDS_CONFIRMATION`:

- Requires at least one `missingConditions` entry.
- May include `nextQuestion` when one follow-up is known.

`INSUFFICIENT_EVIDENCE`:

- Must not include citations.
- Must not assert policy facts.

`LLM_UNAVAILABLE` and `SAFETY_BLOCKED`:

- Must not include `matchedConditions`, `missingConditions`, `citations`, or `nextQuestion`.
- Must not include policy facts, eligibility-like claims, or condition references.

Across all statuses:

- The same `conditionId` cannot appear in both `matchedConditions` and `missingConditions`.
- `citations` cannot repeat the same `evidenceId`.

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

## Scope Note

This AI A0 contract does not define Analysis D0 raw policy data schemas, source classification, processing/review/freshness state axes, file storage conventions, raw source hashes, or privacy collection gates. Those belong in a separate Analysis D0 branch and PR.


## Runtime Contract

AI Phase A1 introduces provider-swappable local generation through `app.llm.LLMProvider`.

Supported providers:

- `ollama`: Calls local Ollama for JSON generation.
- `fake`: Returns a configured `AIOutput` for deterministic tests.
- `template`: Returns the safe `LLM_UNAVAILABLE` fallback without calling a model.

Default Ollama generation settings:

- Model: `qwen3:4b`
- Mode: non-thinking (`think=false`)
- JSON output: `format=json`
- Streaming: disabled (`stream=false`)
- Temperature: `0.1`
- Timeout: `30` seconds

Runtime health checks report `READY`, `MODEL_NOT_INSTALLED`, or `UNAVAILABLE`. Provider failures are contained inside the LLM boundary and must not make the backend process unhealthy by themselves.

Ollama JSON responses are parsed and validated as `AIOutput`. Invalid JSON or schema violations are treated as provider failures, not as eligibility evidence. The LLM runtime must not log prompts, raw sensitive user facts, or full raw model responses.
