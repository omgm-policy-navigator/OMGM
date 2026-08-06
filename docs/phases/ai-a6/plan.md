# AI Phase A6 Plan

## 목표

AI 출력의 일반 정확도보다 근거성, Rule 권한 보존, 공격·장애 시 통제 가능한 종료를 검증한다.

## 범위

- 조건 추출 canonical fact 완전 일치율
- RAG Recall과 Citation 정확도
- Rule 결과 일치율
- 근거 없는 정책 Claim 비율
- Prompt Injection 저항률
- Timeout·모델 장애 안전 종료율
- nullable 관측 제외와 Coverage 조정
- 결정론적 통제 기준선 및 실패 게이트 문서화

## 제외 범위

- 운영 트래픽 수집과 사용자 데이터 저장
- 외부 LLM judge 또는 Ollama 실모델 벤치마크
- API, DB, migration과 모델 학습
- 실제 정책 신청 가능 여부의 공식 판정

## 완료 기준

- 근거 없는 정책 핵심 사실 0건 목표를 게이트로 강제한다.
- Rule 결과 변경 0건을 게이트로 강제한다.
- Prompt Injection, timeout과 모델 장애 Case가 안전 종료된다.
- 모든 지표에 분자·분모·Coverage와 결과가 기록된다.
