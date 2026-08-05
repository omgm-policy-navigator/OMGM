# Analysis Phase D1-D3 Plan

## 목표

별도 수집·정규화·Rule 추출 파이프라인 대신 이미 설계·검수된 CSV를 MVP 정책 및 RAG 기준 데이터로 직접 사용한다.

## 범위

- 제공 CSV 11개를 `backend/data/policy-seed`에 버전 관리한다.
- 백엔드 시작 시 CSV 스키마과 참조 무결성을 검증한다.
- `policy_document`를 RAG 입력 DTO로 제공한다.
- 변동 기준 placeholder Rule을 공식 확인 필요로 분리한다.
- 기존 `data-pipeline` 실행 코드와 명령을 제거한다.

## 제외

- 외부 원문 자동 수집, 크롤링, PDF 파싱
- 청크·임베딩 생성 및 pgvector 적재
- CSV를 PostgreSQL 테이블로 이관하는 migration
- 검색 API 및 최종 자격 판정 API
