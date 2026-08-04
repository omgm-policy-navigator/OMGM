# Data Pipeline

정책 데이터 수집, 원문 보존, 구조화, 조건 후보 추출, 청크 생성, 임베딩 준비, 검수 상태 기록을 담당하는 배치·CLI 작업 영역입니다.

## 실행

```bash
cd data-pipeline
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m policy_pipeline.main
```

샘플 처리:

```bash
python -m policy_pipeline.main --sample ../sample-data/sample-policy.json
```

## 테스트

```bash
cd data-pipeline
source .venv/bin/activate
python -m unittest discover
```

## 외부 API 설정

실제 공공데이터 API, 서울시 Open API, 복지로, 공고문 크롤링은 Phase 0 범위가 아닙니다. API 키는 `.env` 또는 운영 Secret 관리로 주입하고 Git에 커밋하지 않습니다.

관리자 검수 전 조건 후보는 확정 판정 규칙으로 사용하지 않습니다.
