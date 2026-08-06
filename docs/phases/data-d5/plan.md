# Analysis Phase D5 Plan

## 목표

Backend와 AI가 동일한 기대 결과로 Rule, RAG, fact 추출, E2E와 보안 동작을 독립적으로 검증할 수 있는 비민감 평가 기준본을 제공한다.

## 범위

- `rule-engine-cases.json`
- `rag-retrieval-cases.json`
- `fact-extraction-cases.json`
- `e2e-scenarios.json`
- `security-cases.json`
- 공통 JSON Envelope와 버전 계약
- 파일 무결성, 필수 시나리오, Enum 및 실제 Rule/A2 재생 테스트

## 제외 범위

- 운영 사용자 데이터 수집
- 새로운 Rule, 검색 알고리즘, LLM 평가기 또는 API 구현
- 데이터베이스 적재와 migration
- 외부 모델·API가 필요한 품질 점수 측정

## 완료 기준

- 모든 Case가 명시적인 기대 결과를 갖는다.
- happy path, 실패와 경계 Case를 포함한다.
- 지정된 7개 필수 시나리오가 안정적인 tag로 식별된다.
- Backend와 AI CI가 같은 JSON을 Adapter를 통해 사용할 수 있다.
