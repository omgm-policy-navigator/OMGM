# Analysis Phase D4 Progress

## 상태

`analysis-d4-rag-document-processing` 브랜치에서 구현 완료.

## 완료 작업

- SQLAlchemy와 FastAPI에 의존하지 않는 `app.modules.rag` 문서 가공 모듈을 추가했다.
- 제목, 조항, 문단, 문장 의미 변화와 Markdown 표 행 분할을 구현했다.
- 문서 유형 4종과 Chunk 의미 유형 9종을 정의했다.
- 혼합 의미, 1,000자 초과, 위치 누락, 짧은 기타 문맥을 품질 문제로 검출한다.
- 연락처 Chunk는 필요성과 공개 범위를 검수하기 전까지 임베딩 입력에서 제외한다.
- 검수 필요 Chunk가 임베딩 입력으로 승격되지 않도록 차단했다.
- Chunk ID와 콘텐츠 SHA-256을 결정적으로 생성한다.
- 검수된 Overview 38건을 정책·문서 ID, URL, 위치와 연결한 `10_policy_document_chunk.csv`를 생성했다.
- Seed 로더가 Chunk 참조·Enum·URL·위치·해시를 검증하고 승인된 Chunk만 노출하도록 확장했다.
- RAG 흐름, 모듈 경계, 데이터 소유권, 저장 모델과 운영 문서를 갱신했다.

## 데이터 제한

- 현재 38개 입력은 전체 공고문이 아니라 D1-D3에서 검수된 정책 Overview다.
- 따라서 Seed 위치는 기존 CSV의 행과 content 필드를 가리키며 세부 공고 조항 위치를 가장하지 않는다.
- 전체 공고문 수집과 PDF·HTML 변환은 MVP 런타임 범위 밖이다.
- 실제 embedding 열은 비어 있고 벡터 생성·적재는 후속 Phase로 남긴다.

## PR #16 Review Follow-up

- 표 행의 강제 `TABLE_ROW` 분류와 무관하게 연락처 cue, 전화번호, 이메일을 내용에서 검사한다.
- 임베딩 Seed 생성 API를 승인 Chunk 필터링 계약으로 통일했다.
- Chunk의 문서 유형이 부모 문서와 일치하는지 검증한다.
- 표 열 불일치는 `table_column_mismatch`로 검수 대상이 된다.
- Markdown escaped pipe를 하나의 셀 값으로 보존한다.
- 의미 분류와 혼합 의미 검수가 제목과 본문을 동일하게 사용한다.
