# D5 공통 평가 데이터

이 디렉터리는 Backend와 AI CI가 같은 기대 결과를 사용할 수 있도록 만든 비민감 JSON 기준본이다.

- 모든 파일은 UTF-8 JSON이며 루트에 `schemaVersion`, `dataset`, `cases`를 둔다.
- 각 Case는 전역 고유 `id`, 설명용 `title`, 시나리오 분류 `tags`, `input`, 명시적 `expected`를 갖는다.
- 값은 합성 예시이며 실제 개인정보, 실제 신청 기록, 비밀정보를 포함하지 않는다.
- `expected`는 현재 Rule Engine, A2 추출, A4 검색, A5 근거 제한 계약의 Enum과 필드명을 사용한다.
- CI 소비자는 알 수 없는 필드를 허용하더라도 `schemaVersion`의 major가 다르면 실패해야 한다.

파일별 책임:

- `rule-engine-cases.json`: 결정론적 Rule 결과와 신청기간 경계
- `rag-retrieval-cases.json`: 정책·상태·신뢰도 필터와 근거 부족
- `fact-extraction-cases.json`: 허용 키, 모호성, 기존 사실 충돌
- `e2e-scenarios.json`: 질문부터 판정·검색·설명까지 단계별 기대 결과
- `security-cases.json`: Prompt injection, Citation, URL, 입력 크기와 로그 금지

검증은 `pytest tests/unit/test_evaluation_datasets.py`로 실행한다.
