# Analysis Phase D3 Progress

## 완료 작업

- 검수 기준본 133개 Rule을 공식 URL·근거 위치·추출 방식·관리자 상태가 포함된 `policy_rule_seed.csv`로 파생했다.
- 기준본 위치와 공식 문서 내부 위치를 분리했다. 공식 내부 위치가 확인되지 않은 133개 Rule은 모두 `NEEDS_OFFICIAL_CONFIRMATION`으로 보수적으로 분류했다.
- 검수된 질문 49개를 `question_seed.csv`로 생성했다.
- 정책 관계 24개에 양쪽 정책 URL과 기준본 위치를 연결했다. 공식 관계 근거 위치가 없으므로 모두 `NEEDS_OFFICIAL_CONFIRMATION`으로 분류했다.
- 파생 산출물의 ID와 행 수가 기존 03·04·07 기준본과 일치하는지 테스트한다.
- 모든 Rule 후보가 근거 문구, 공식 HTTP(S) URL과 기준본 내 재현 위치를 갖는지 검증하고, 공식 내부 위치가 없으면 승인되지 않도록 강제한다.

## 제한사항

- 기존 MVP 기준본은 자동 추출 실행 로그를 보존하지 않아 `extraction_method=REVIEWED_CSV_BASELINE`으로 정직하게 표시한다.
- `baseline_source_location`은 관리자 검수 기준본의 근거 행·필드 위치이며 `official_source_location`과 구분한다.
- 공식 페이지 내 조항 좌표가 없는 조건은 확정 위치를 꾸며내지 않으며 필요 시 공식 확인 상태를 유지한다.
