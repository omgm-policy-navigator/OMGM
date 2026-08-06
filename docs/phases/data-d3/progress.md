# Analysis Phase D3 Progress

## 완료 작업

- 검수 기준본 133개 Rule을 공식 URL·근거 위치·추출 방식·관리자 상태가 포함된 `policy_rule_seed.csv`로 파생했다.
- 102개 결정형 Rule은 `APPROVED`, 원문 기준 재확인이 필요한 31개 Rule은 `NEEDS_OFFICIAL_CONFIRMATION`으로 보존했다.
- 검수된 질문 49개를 `question_seed.csv`로 생성했다.
- 검수된 정책 관계 24개를 `policy_relation_seed.csv`로 생성했다.
- 파생 산출물의 ID와 행 수가 기존 03·04·07 기준본과 일치하는지 테스트한다.
- 모든 Rule 후보가 근거 문구, 공식 HTTP(S) URL과 기준본 내 재현 위치를 갖는지 검증한다.

## 제한사항

- 기존 MVP 기준본은 자동 추출 실행 로그를 보존하지 않아 `extraction_method=REVIEWED_CSV_BASELINE`으로 정직하게 표시한다.
- `source_location`은 공식 페이지의 조항 좌표가 아니라 관리자 검수 기준본의 근거 행·필드 위치다.
- 공식 페이지 내 조항 좌표가 없는 조건은 확정 위치를 꾸며내지 않으며 필요 시 공식 확인 상태를 유지한다.
