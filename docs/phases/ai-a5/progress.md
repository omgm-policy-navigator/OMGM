# AI Phase A5 Progress

## 완료 작업

- `app.modules.explanations`에 FastAPI·SQLAlchemy와 독립적인 A5 입력/출력 DTO를 추가했다.
- LLM에는 이미 계산된 Rule 상태와 조건, 검색된 Chunk, 선택 그래프 노드만 전달하고 판정 변경을 금지하는 Prompt를 구성했다.
- 최종 판정 요약, 충족 조건, 추가 확인 조건과 공식 출처는 LLM 응답이 아니라 구조화된 입력에서 조립한다.
- LLM의 `resultStatus`, 충족·확인 조건 ID와 Citation이 입력 계약과 일치하는지 검증한다.
- 인용 Chunk에 없는 금액·날짜·비율·나이·기간 수치가 설명에 나타나면 초안을 폐기한다.
- Rule 결과와 반대되는 명시적 신청 가능·불가 표현이 나타나면 안전 fallback으로 교체한다.
- Citation이 없으면 LLM을 호출하지 않고 `OFFICIAL_CONFIRMATION_REQUIRED` 설명 상태와 빈 공식 출처를 반환한다.
- 정책 설명과 일반 안내를 `policyExplanation`, `generalGuidance`로 분리했다.

## 제한사항

- A5는 설명 생성 모듈만 제공하며 HTTP API에는 아직 연결하지 않는다.
- 반대 문장 검사는 한국어·영어의 명시적 자격 표현을 차단한다. 최종 판정과 조건은 항상 결정론적 필드가 권위값이다.
- 신청 시점은 수치를 추론하지 않고 공식 공고 확인 안내만 제공한다.
