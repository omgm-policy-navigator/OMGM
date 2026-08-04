# Infra

Docker Compose 기반 로컬 인프라를 관리합니다.

## 구성

- PostgreSQL: 정형 정책, 사용자 사실, 판정, 관계 데이터를 저장합니다.
- pgvector: PostgreSQL 확장으로 정책 문서 청크 임베딩을 저장합니다.
- Ollama: 로컬 생성 모델과 임베딩 모델을 실행합니다.

## 실행

```bash
docker compose up -d postgres ollama
docker compose ps
```

전체 앱 실행:

```bash
docker compose up --build
```

## 볼륨과 로컬 데이터

PostgreSQL 데이터와 Ollama 모델 데이터는 Docker 볼륨에 저장됩니다. 로컬 데이터 디렉터리와 모델 데이터는 Git에 포함하지 않습니다.

## 초기화

`infra/postgres/init/001-enable-pgvector.sql`에서 pgvector 확장을 활성화합니다.
