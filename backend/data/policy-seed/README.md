# 신혼부부 정책 Seed Data

검증 기준일: 2026-08-05
대상: 서울 거주·서울 생활권의 예비·신혼부부를 중심으로 서울시 및 중앙정부 정책
정책 수: 38개
규칙 수: 133개
질문 수: 49개
관계 수: 24개
RAG Chunk 수: 38개

## 파일
- 01_category.csv: 5개 정책 분야
- 02_policy.csv: 정책 기본정보
- 03_policy_rule.csv: 정규화한 판정 규칙
- 04_question.csv: 사용자 조건 수집 질문
- 05_user_fact_template.csv: 사용자 응답 저장용 빈 템플릿
- 06_policy_evaluation_template.csv: 판정 결과 저장용 빈 템플릿
- 07_policy_relation.csv: 선후·대안·충돌·재평가 관계
- 08_policy_document.csv: RAG용 정책 개요 문서
- 09_policy_flat.csv: 빠른 MVP·분석용 통합 파일
- 10_policy_document_chunk.csv: 검수된 RAG Chunk와 임베딩 입력 Seed
- policy_rule_seed.csv: 공식 URL·근거 위치·검수 상태를 포함한 D3 Rule 후보 산출물
- question_seed.csv: 관리자 검수된 D3 사용자 질문 산출물
- policy_relation_seed.csv: 관리자 검수된 D3 정책 관계 산출물

## 중요 주의사항
1. 이 데이터는 MVP Seed Data이며 공식 자격 판정을 대체하지 않습니다.
2. 공공임대는 단지·회차별 모집공고에 따라 조건이 달라집니다.
3. 대출 금리·한도·소득·자산 기준은 접수일과 금융기관 심사에 따라 달라질 수 있습니다.
4. 서울시 사업은 예산 소진, 연도별 공고, 시범사업 종료·개편 가능성이 있습니다.
5. `evaluation_mode=OFFICIAL_CONFIRMATION_REQUIRED` Rule은 공식 기준 확인 전 결정형 판정에서 제외합니다.
6. CSV는 Excel 한글 깨짐 방지를 위해 UTF-8 BOM으로 저장했습니다.
7. Chunk는 `source_url`과 `source_location`을 반드시 가지며 `APPROVED` 행만 임베딩 입력으로 사용합니다.
8. D3 파생 Seed는 기존 03·04·07 기준본을 대체하지 않으며 검수·근거 확인용 산출물입니다.

## 질문과 Rule 값 계약

- 질문 선택지는 `{"label":"혼인신고 완료","value":"MARRIED"}` 형태이며 UI에는 `label`, 사용자 사실과 Rule 비교에는 `value`를 사용합니다.
- `show_condition`은 `condition_key`, `operator`, `value` 세 필드를 정확히 사용하며 `value`도 canonical value입니다.
- Rule의 `evaluation_mode`가 `DETERMINISTIC`인 경우에만 구조화된 사용자 사실과 비교합니다.
- 결정형 Rule은 `review_status=APPROVED`여야 하며, 공식 확인 필요 Rule은 `DRAFT`로 격리합니다.

수동 원문 확인과 Seed 갱신 절차는 [정책 Seed 운영 가이드](../../../docs/data/policy-seed-operations.md)를 따릅니다.

## 권장 적재 순서
category → policy → question → policy_rule → policy_relation → policy_document → policy_document_chunk

## 추천 MVP 판정 방식
- required=true 규칙 실패: LIKELY_INELIGIBLE
- 필수 규칙 중 응답 없음: NEEDS_CONFIRMATION
- 시점이 미래 조건: AVAILABLE_LATER
- 모두 충족하나 공고·금융기관 확인 필요: OFFICIAL_CONFIRMATION_REQUIRED
- 모두 충족하고 현재 접수 가능: LIKELY_ELIGIBLE
