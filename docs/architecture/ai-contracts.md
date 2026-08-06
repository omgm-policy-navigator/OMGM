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
  "answer": "공고�?기�??�로 거주 지??조건?� 충족?�니??",
  "resultStatus": "ANSWERED",
  "is_fallback": false,
  "matchedConditions": [
    {
      "conditionId": "region",
      "label": "거주 지??,
      "reason": "?�울 거주"
    }
  ],
  "missingConditions": [],
  "citations": [
    {
      "sourceId": "doc_1",
      "title": "?�혼부부 주거 지??공고",
      "url": "https://example.go.kr/policy/1",
      "policyVersionId": "policy_version_1",
      "evidenceId": "chunk_1",
      "excerpt": "공고문에???�인??근거 문구"
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


extQuestion` is either
ull` or one follow-up question with `questionId`, `prompt`, and `factKey`.

`is_fallback` is response metadata. It is `false` for primary provider output and `true` when the runtime returned a template or static safety-net response after provider failure.

Text and identifier fields are non-empty. `answer` is capped so LLM output cannot grow without bound.

## Status Invariants

`ANSWERED`:

- Requires at least one citation.
- Must not include `missingConditions`.
- Must set
extQuestion` to
ull`.

`NEEDS_CONFIRMATION`:

- Requires at least one `missingConditions` entry.
- May include
extQuestion` when one follow-up is known.

`INSUFFICIENT_EVIDENCE`:

- Must not include citations.
- Must not assert policy facts.

`LLM_UNAVAILABLE` and `SAFETY_BLOCKED`:

- Must not include `matchedConditions`, `missingConditions`, `citations`, or
extQuestion`.
- Must not include policy facts, eligibility-like claims, or condition references.

Across all statuses:

- The same `conditionId` cannot appear in both `matchedConditions` and `missingConditions`.
- `citations` cannot repeat the same `evidenceId`.

## Fallback Contract

When the LLM is unavailable, the backend returns:

```json
{
  "answer": "?�재 AI ?�명???�성?????�습?�다. 구조?�된 ?�정 결과?� 근거�??�인??주세??",
  "resultStatus": "LLM_UNAVAILABLE",
  "matchedConditions": [],
  "missingConditions": [],
  "citations": [],
  "nextQuestion": null
}
```

When RAG evidence is insufficient, the backend returns `INSUFFICIENT_EVIDENCE`, leaves `citations` empty, and does not invent policy facts.

When required user facts are missing, the backend returns `NEEDS_CONFIRMATION` with `missingConditions` and, when available,
extQuestion`.

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

Runtime health checks report `READY`, `MODEL_NOT_INSTALLED`, or `UNAVAILABLE`. Provider failures are contained inside the LLM boundary and must not make the backend process unhealthy by themselves. `create_available_llm_provider` falls back to the template provider when the configured provider is not ready. `RobustLLMManager` wraps generation so primary failure, fallback failure, and static safety-net fallback all return validated `AIOutput` instead of propagating provider exceptions to API callers.

Ollama uses an explicit async `httpx.Timeout` with the configured timeout value. Ollama JSON responses are extracted from pure JSON, fenced JSON, or surrounding explanatory text and then validated as `AIOutput`. Invalid JSON or schema violations are treated as provider failures, not as eligibility evidence. The LLM runtime must not log prompts, raw sensitive user facts, or full raw model responses.

## Phase A2 User Condition Extraction

Phase A2 adds the `app.modules.user_facts` prompt and strict output contract. The only allowed extraction keys are `MARRIAGE_STATUS`, `RESIDENCE_REGION`, `HOME_OWNERSHIP`, `HOUSEHOLD_INCOME_RANGE`, `CONTRACT_STATUS`, `PREGNANCY_STAGE`, and `CHILD_AGE_RANGE`.

Each candidate contains `factKey`, `value`, `confidence`, `isAmbiguous`, and a short user-supported `evidence` phrase. Unknown keys, extra fields, duplicate keys, blank values, and confidence outside `0..1` invalidate the complete model response. Missing facts are omitted rather than inferred or converted to `false` or `0`.

Backend code requires confirmation when confidence is below `0.8`, the evidence phrase is not present in the normalized user text, the candidate is ambiguous, or it differs from an existing confirmed fact. Duplicate confirmed facts for one key are rejected instead of being resolved by input order. Reviewed candidates expose `raw_value` and `requires_normalization=true` so downstream code cannot mistake free-form model text for a canonical domain value. A2 returns candidate and conflict-review DTOs only; it adds no API, persistence, eligibility calculation, or `user_fact` table.

## Phase A3-A4 Embedding and Retrieval

A3 uses `qwen3-embedding:0.6b` with a fixed 1024-dimensional storage contract. Only D4 `APPROVED` chunks belonging to `ACTIVE` policies are indexed. Chunk types exposed to retrieval are `OVERVIEW`, `ELIGIBILITY`, `APPLICATION`, `DOCUMENTS`, `FAQ`, and `CAUTION`.

A4 retrieval requires an explicit selected `policy_id` and filters `document_status=APPROVED`, `trust_level=OFFICIAL`, `policy_status=ACTIVE`, and the configured embedding model before applying the cosine similarity threshold and Top K limit. Citation DTOs include document ID, chunk evidence ID, policy version, public source URL, source location, excerpt, and similarity. No matching evidence returns an explicit insufficient-evidence result with no citations; retrieval never expands the policy candidate set or changes eligibility.

## Phase A5 Rule-grounded Answer Generation

A5 accepts the user question and conditions, a completed Rule Engine `EvaluationResult`, retrieved Citation chunks, and an optional selected graph node. The LLM selects and references approved evidence, but its free-form answer is not exposed as a policy fact. Backend code owns the final eligibility status, satisfied, unsatisfied, and confirmation condition lists, official sources, policy-evidence rendering, application-timing guidance, and next action.

The draft is discarded when it is marked as fallback, has no Citation, its `resultStatus` differs from the Rule result, condition IDs differ, a Citation is not present in retrieved evidence, an explicit eligibility statement opposes the Rule status, or a policy number is absent from every retrieved excerpt. Only Citation IDs actually returned by the validated draft become `officialSources`; `policyExplanation` is assembled verbatim from those approved excerpts so unsupported qualitative claims in the free-form draft cannot reach the response. Rule condition IDs must be present and globally unique across result groups. Input question, condition, Citation, and graph-node sizes are bounded before prompt construction. Missing citations skip the LLM call and return `explanationStatus=OFFICIAL_CONFIRMATION_REQUIRED` without policy-detail assertions. Policy evidence and non-authoritative general guidance remain separate fields.

## Phase A6 Quality and Safety Evaluation

A6 evaluates controlled observations without FastAPI, SQLAlchemy, or an external model. The observation contract records expected and actual extracted facts, relevant and retrieved evidence IDs, allowed and emitted Citation IDs, Rule statuses, grounded policy-claim counts, Prompt Injection outcomes, and failure termination outcomes.

Metrics report numerator, denominator, target, direction, applicable and evaluated Case counts, and Coverage. A nullable signal is excluded from the calculation and lowers Coverage; it is never converted to a failure, `false`, or `0`. A metric with zero evidence or incomplete Coverage cannot pass.

The controlled safety gate requires extracted-fact Case exact match and fact-value accuracy, full RAG Recall, Citation precision and required-Citation recall, Rule result agreement, Prompt Injection resistance, safe failure termination, and zero ungrounded policy claims. Trigger/result safety fields must be provided together and a result requires a true trigger. Metrics without applicable evidence are `NOT_APPLICABLE`; partial suites ignore them, while the separate A6 baseline validator requires every metric with full Coverage. Any Rule result change, ungrounded policy claim, or unsafe timeout/model-failure termination fails the complete baseline. The baseline Adapter creates actual observations by executing A2 parsing/review, Rule evaluation, RAG search, and A5 generation with deterministic fake providers; it does not trust hand-authored `actual*` fixture fields. This validates control boundaries and does not claim production-model quality or statistical generalization.
