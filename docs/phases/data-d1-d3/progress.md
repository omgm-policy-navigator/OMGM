# Analysis Phase D1-D3 Progress

## 완료

- 제공 데이터 규모: 카테고리 5, 정책 38, 질문 49, Rule 133, 관계 24, RAG 문서 38.
- 원래 목표의 12개 대신 제공 기준본의 38개 정책 전체를 채택했다.
- CSV 기준본을 백엔드 이미지에 포함하고 시작 시 읽기 전용으로 로딩한다.
- 중복 ID, 참조, HTTP(S) URL, 정책별 문서 연결을 검증한다.
- `SHA256SUMS`로 제공 파일 11개의 변경 여부를 시작 시 검증한다.
- 명시적 `evaluation_mode`로 공식 확인 필요 Rule 31개와 결정형 Rule 102개를 분리한다.
- 결정형 Rule 102개는 `review_status=APPROVED`, 공식 확인 필요 Rule 31개는 `DRAFT`로 격리한다.
- 질문 옵션을 `{label, value}`로 변경해 UI 표시값과 Rule canonical value를 연결했다.
- `show_condition` 전용 스키마, strict boolean/header/enum/date 검증을 추가했다.
- 기존 데이터 파이프라인 폴더, 실행 명령, 구조 검증 항목을 제거했다.

## 계약

- `policy.id`는 CSV의 값을 Canonical ID로 유지한다.
- 동일 정책의 Rule과 문서는 `policy_id`로 연결한다.
- `08_policy_document.csv`는 임베딩 전 RAG 문서 입력이다.
- 빈 사용자 사실·평가 template은 개인정보 저장소가 아니라 스키마 참고 자료다.
- 사용자 답변은 질문 option의 `label`이 아니라 canonical `value`로 저장·비교한다.
