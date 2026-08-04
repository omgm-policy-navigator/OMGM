# Ollama

로컬 LLM 실행 환경입니다. 모델 다운로드는 이미지 빌드 중 자동 실행하지 않고 명시적으로 실행합니다.

```bash
OLLAMA_GENERATION_MODEL=qwen3:4b OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b ./infra/ollama/pull-models.sh
```

Ollama는 조건 후보 추출 보조, 질문 이해, 검색 질의 보정, 설명 생성에 사용합니다. 최종 자격 상태는 Rule Engine이 계산합니다.
