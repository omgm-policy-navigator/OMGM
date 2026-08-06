# Analysis Phase D5 Progress

## 완료 작업

- `backend/tests/fixtures/evaluation`에 5개 평가 데이터셋과 소비자 README를 추가했다.
- 다섯 파일이 `schemaVersion`, `dataset`, `cases` 공통 Envelope를 사용하도록 통일했다.
- 모든 조건 충족, 소득 모름, 혼인 상태 충돌, 신청기간 종료, 향후 조건 충족, 공식 근거 부족, 정책 원문 변경 시나리오를 포함했다.
- happy path뿐 아니라 metadata 혼입, 허용되지 않은 fact key, Prompt injection, Citation 위조, 비공개 URL, 입력 크기 등 실패·경계 Case를 포함했다.
- 실제 개인정보·소득액·신청 기록 대신 합성 식별자와 합성 값을 사용했다.
- Rule Case를 현재 Rule Engine에서, fact Case를 A2 파서·검토 로직에서, RAG Case를 검색 서비스와 Citation 변환에서 재생하는 테스트를 추가했다.
- E2E Case가 실행 가능한 Rule·Fact·RAG Case를 명시적으로 참조하도록 바꾸고 기대 상태의 참조 무결성을 검증한다.
- Security Case의 비공개 Citation URL과 과대 입력을 실제 DTO·함수에 전달하며, 모든 JSON에 개인정보 패턴과 비밀정보 키 검사를 적용한다.
- 공통 계약과 CI Adapter 원칙을 `docs/data/evaluation-datasets.md`에 기록했다.

## 제한사항

- D5는 고정 평가 기준본을 제공하며 자동 LLM 의미 채점이나 외부 모델 호출은 포함하지 않는다.
- 각 CI는 공통 JSON을 자신의 repository/API DTO로 변환하는 얇은 Adapter가 필요하지만 숨은 Rule·Chunk 값은 추가할 수 없다.
- 현재 D4 기준본이 Overview 중심이므로 세부 공고문이 확충되면 retrieval Case를 추가해야 한다.
