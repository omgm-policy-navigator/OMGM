# AI Phase A5 Plan

## 목표

LLM이 새 판정을 만들지 않고 기존 Rule Engine 결과와 승인된 RAG 근거를 사용자에게 설명한다.

## 범위

- 사용자 질문·조건, Rule 결과, 검색 Citation, 선택 그래프 노드 입력 계약
- 판정 요약, 충족 조건, 추가 확인 조건, 신청 시점, 공식 출처, 다음 행동 출력 계약
- 기존 `AIOutput`을 사용하는 설명 Prompt
- Rule 상태·조건 ID·Citation·정책 수치 사후 검증
- 근거 부족, LLM 실패와 안전 검증 실패 시 결정론적 fallback
- 정책 설명과 일반 안내의 필드 분리

## 제외 범위

- Rule Engine 계산 또는 상태 변경
- RAG 검색과 그래프 Projection 변경
- HTTP API와 대화 오케스트레이션
- 설명 결과 저장과 신규 DB 테이블
