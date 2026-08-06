# D5 Rule·RAG·E2E 평가 데이터 계약

## 목적과 위치

D5 기준본은 [`backend/tests/fixtures/evaluation`](../../backend/tests/fixtures/evaluation/README.md)에 있다. Backend와 AI CI는 별도 복사본을 만들지 않고 동일 JSON을 읽는다. 데이터는 합성된 비민감 예시이며 실제 사용자 사실이나 실제 신청 기록이 아니다.

## 공통 Envelope

각 파일은 다음 구조를 사용한다.

```json
{
  "schemaVersion": "1.0",
  "dataset": "rule-engine",
  "cases": [
    {
      "id": "rule-all-required-met",
      "title": "모든 필수 조건 충족",
      "tags": ["all_conditions_met", "happy_path"],
      "input": {},
      "expected": {}
    }
  ]
}
```

- `schemaVersion`: 소비자 호환성 판단용 계약 버전. 현재 major는 `1`이다.
- `dataset`: 파일 책임을 식별하는 안정적인 이름이다.
- `id`: 다섯 파일 전체에서 고유한 Case ID다.
- `tags`: 필수 시나리오 및 happy/failure/boundary 분류다.
- `input`: 실행 모듈에 전달하거나 Adapter가 변환할 입력이다.
- `expected`: 상태, 근거 ID, 충돌, fallback 등 명시적 기대 결과다.

CI Adapter는 모듈별 DTO 차이를 변환할 수 있지만 `expected`의 의미를 변경해서는 안 된다. `major.minor` 형식과 major `1`을 검증하며 같은 major의 minor 변경과 알 수 없는 선택 필드는 호환 가능하다.

## 데이터셋 책임

- `rule-engine-cases.json`: 현재 Rule Engine에서 직접 재생 가능한 조건, 사실, 고정 평가일, 신청기간과 기대 상태
- `rag-retrieval-cases.json`: 실제 `SearchHit` 생성에 필요한 문서·버전·본문·URL·위치 메타데이터와 정확한 기대 Citation 값
- `fact-extraction-cases.json`: A2 허용 Enum, 모호성, confidence, 기존 확정 사실 충돌과 저장 금지 기대값
- `e2e-scenarios.json`: `ruleCaseId`, `factCaseId`, `retrievalCaseId`로 실행 가능한 구성요소 Case를 연결하고 설명 상태와 재색인·재평가를 단계별로 명시한 시나리오
- `security-cases.json`: Prompt injection, Citation 무결성, 비공개 URL, 로그 데이터, 입력 크기 제한

## 불변 조건

- 누락된 값은 `false` 또는 `0`으로 변환하지 않는다.
- 충돌 후보는 기존 확정 사실을 덮어쓰지 않고 사용자 재확인을 요구한다.
- 이전 버전·비활성·비공식·다른 정책 Chunk는 검색 결과에 포함하지 않는다.
- 공식 근거가 없으면 정책 사실을 생성하지 않고 근거 부족 상태를 반환한다.
- 정책 버전이 변경되면 기존 판정은 `STALE`이며 재평가와 재색인이 필요하다.
- 보안 Case의 사용자 값은 합성값만 사용하고 prompt, 원문 사실, 모델 원응답을 로그 기대값에 넣지 않는다.

## 검증

`backend/tests/unit/test_evaluation_datasets.py`는 파일 목록, Envelope, Case ID 유일성, 필수 시나리오 포함 여부, Enum을 검증한다. Rule Case는 실제 Rule Engine으로, fact Case는 실제 A2 파서와 검토 로직으로, RAG Case는 실제 검색 서비스와 `SearchHit`→Citation 변환으로 재생한다. Security Case는 실제 Citation URL 및 A2 입력 크기 경계를 호출한다. E2E Case의 구성요소 참조와 기대 상태도 실행된 데이터셋 사이에서 검증한다. 개인정보 패턴과 비밀정보 키 검사는 다섯 JSON 전체에 적용한다.
