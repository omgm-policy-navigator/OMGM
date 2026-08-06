# AI Phase A6 Progress

## 완료 작업

- FastAPI와 SQLAlchemy에 의존하지 않는 `app.modules.ai_evaluation` 평가 경계를 추가했다.
- 조건 추출 fact 완전 일치, RAG Recall, Citation 정확도, Rule 일치, 무근거 Claim, Prompt Injection, 안전 장애 종료 지표를 구현했다.
- 각 지표에 분자·분모, 방향, 목표, 적용·평가 Case 수와 Coverage를 제공한다.
- nullable 기대·실제 신호는 계산에서 제외하고 Coverage를 낮추며 불완전 Coverage는 통과하지 못하게 했다.
- Rule 결과 변경, 무근거 정책 Claim과 unsafe failure 수를 전체 보고서에 명시하고 하나라도 발생하면 실패하게 했다.
- 합성 관측값 8건의 통제 기준선과 의도적 회귀·Coverage 결손 테스트를 추가했다.
- 기준선 결과와 해석 한계를 `docs/evaluation/ai-a6-controlled-baseline.md`에 기록했다.

## 제한사항

- 통제 기준선은 외부 모델을 호출하지 않아 운영 모델의 비결정적 품질이나 성능을 대표하지 않는다.
- 표본은 안전 계약 회귀용 소규모 합성 Case이며 정책·질의별 통계적 신뢰구간을 제공하지 않는다.
- 실제 모델 평가는 개인정보가 제거된 별도 승인 데이터와 고정 모델 버전이 준비된 뒤 동일 관측 계약으로 확장해야 한다.
