# Analysis Phase D3 Plan

## 목표

검수된 정책 기준본에서 Rule 후보, 사용자 질문과 정책 관계 산출물을 만들고 근거·검수 상태를 명시한다.

## 범위

- `policy_rule_seed.csv`, `question_seed.csv`, `policy_relation_seed.csv` 생성
- Rule별 정책 ID, 질문 ID, 공식 URL, 근거 문구와 재현 위치 연결
- 관리자 검수 상태와 평가 가능 모드 분리
- 공식 확인이 필요한 Rule의 결정형 평가 제외 상태 보존
- 파생 Seed와 기존 03·04·07 기준본의 동기화 검증

## 제외 범위

- 외부 원문 자동 수집과 신규 LLM 추출 실행
- 관리자 검수 UI/API
- Rule Engine 또는 질문 API 계약 변경
- DB 스키마와 migration 변경
