# 신혼부부 정책 Seed Data

검증 기준일: 2026-08-05
대상: 서울 거주·서울 생활권의 예비·신혼부부를 중심으로 서울시 및 중앙정부 정책
정책 수: 38개
규칙 수: 133개
질문 수: 49개
관계 수: 24개

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

## 중요 주의사항
1. 이 데이터는 MVP Seed Data이며 공식 자격 판정을 대체하지 않습니다.
2. 공공임대는 단지·회차별 모집공고에 따라 조건이 달라집니다.
3. 대출 금리·한도·소득·자산 기준은 접수일과 금융기관 심사에 따라 달라질 수 있습니다.
4. 서울시 사업은 예산 소진, 연도별 공고, 시범사업 종료·개편 가능성이 있습니다.
5. `OFFICIAL_THRESHOLD`, `ANNOUNCEMENT_THRESHOLD`, `OFFICIAL_PERIOD` 값은 운영 시 공식 원문 수집기로 치환해야 합니다.
6. CSV는 Excel 한글 깨짐 방지를 위해 UTF-8 BOM으로 저장했습니다.

## 권장 적재 순서
category → policy → question → policy_rule → policy_relation → policy_document

## 추천 MVP 판정 방식
- required=true 규칙 실패: LIKELY_INELIGIBLE
- 필수 규칙 중 응답 없음: NEEDS_CONFIRMATION
- 시점이 미래 조건: AVAILABLE_LATER
- 모두 충족하나 공고·금융기관 확인 필요: OFFICIAL_CONFIRMATION_REQUIRED
- 모두 충족하고 현재 접수 가능: LIKELY_ELIGIBLE
