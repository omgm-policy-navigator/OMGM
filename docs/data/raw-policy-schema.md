# Raw Policy Schema

## 목적과 경계

D0는 수집한 정책 원문을 재현 가능하게 보존하는 계약을 정의한다. Raw는 수집 당시의 바이트와 메타데이터이며 수정하지 않는다. 텍스트 변환, 정규화, 조건 후보, 청크, 임베딩 입력은 Processed 산출물이고 Raw를 덮어쓰지 않는다.

이 계약은 파일 기반 원본 보관 계약이다. SQLAlchemy 모델, Alembic migration, 수집기, 관리자 검수 API, 게시 DB 반영은 D0 범위가 아니다.

## Raw Policy Metadata 1.0

각 원문 파일에는 같은 basename의 `.metadata.json` sidecar를 둔다. 기계 판독 계약은 [`data-pipeline/schemas/raw-policy.schema.json`](../../data-pipeline/schemas/raw-policy.schema.json), Python 경계 검증은 `policy_pipeline.raw_policy.RawPolicyMetadata`에 있다.

| 필드 | 형식 | 필수 | 기준 |
| --- | --- | --- | --- |
| `schema_version` | string | 예 | D0는 `1.0` |
| `raw_policy_id` | string | 예 | 3~64자 소문자 영문·숫자·`_`·`-`, 수집 레코드의 안정 식별자 |
| `source_authority` | enum | 예 | `OFFICIAL` 또는 `SECONDARY` |
| `source_format` | enum | 예 | `API_JSON`, `HTML`, `PDF`, `DOCUMENT`, `TEXT` |
| `source_url` | URL | 예 | 절대 HTTP(S) URL. 자격 증명과 secret query parameter 금지 |
| `publisher` | string | 예 | 문서를 게시한 기관 또는 매체 |
| `collected_at` | datetime | 예 | 실제 원문을 받은 UTC 시각, ISO 8601 |
| `content_sha256` | string | 예 | 저장한 원문 바이트 전체의 소문자 SHA-256 |
| `media_type` | string | 예 | 응답 또는 파일의 media type |
| `original_filename` | string/null | 아니요 | 경로가 제거된 원래 basename |
| `collector` | string | 예 | 수집 방식/구현 식별자. 기본값 `manual` |
| `status` | enum | 예 | 아래 검수 상태. 최초값 `COLLECTED` |
| `status_updated_at` | datetime/null | 아니요 | 상태를 마지막으로 변경한 UTC 시각 |

HTTP status, ETag, Last-Modified 같은 전송 진단값은 수집기 구현 Phase에서 별도 수집 이벤트로 확장할 수 있다. D0 필수 계약에는 넣지 않는다. API key, cookie, Authorization header, 전체 요청/응답 header는 저장하지 않는다.

## 출처 구분

- `OFFICIAL`: 정책을 결정·집행하거나 공식 공고를 위임받은 정부·지자체·공공기관의 원문, 공식 API 또는 공식 게시 페이지.
- `SECONDARY`: 언론 기사, 블로그, 커뮤니티, 포털 재가공 페이지, 기관이 아닌 제3자의 요약·해설.

도메인 형태만으로 공식 여부를 자동 확정하지 않는다. 공식 기관의 보도자료는 공식 원문이 될 수 있지만, 공식 문서를 인용한 언론 기사는 `SECONDARY`다. `SECONDARY`는 탐색과 교차 확인에 쓸 수 있으나 단독으로 승인된 자격 규칙이나 최종 판정 근거가 될 수 없다.

## 원본 데이터 상태

| 상태 | 의미 |
| --- | --- |
| `COLLECTED` | 원문과 필수 메타데이터 및 해시가 보존됨 |
| `EXTRACTED` | Raw에서 Processed 후보가 생성됨 |
| `REVIEWING` | 담당자가 출처와 추출 후보를 검수 중 |
| `APPROVED` | 공식성·무결성·가공 결과가 검수되어 게시 준비 가능 |
| `REJECTED` | 출처 부적합, 손상, 중복 등으로 사용하지 않음 |
| `OUTDATED` | 더 최신 공식 원문이 확인되어 현재 근거로 사용하지 않음 |

상태는 원문 바이트를 변경하지 않는다. 같은 URL의 바이트가 바뀌면 기존 Raw를 수정하지 않고 새 `raw_policy_id`와 해시로 수집한다. 승인 전 추출 후보는 Rule Engine이나 RAG의 게시 근거로 사용하지 않는다.

## 파일명과 폴더 규칙

환경변수로 지정한 루트 아래에서 Raw와 Processed를 물리적으로 분리한다.

```text
data/
  raw/YYYY/MM/DD/{official|secondary}/{source-slug}/
    {raw-policy-id}__{sha256-first-12}.{ext}
    {raw-policy-id}__{sha256-first-12}.metadata.json
  processed/{raw-policy-id}/{processor-version}/
    ... derived artifacts ...
```

- 경로 날짜는 `collected_at`의 UTC 날짜다.
- `source-slug`는 3~64자의 소문자 kebab-case다.
- 확장자는 실제 보관 형식과 일치하는 1~8자 소문자 영숫자다.
- Processed 산출물은 `raw_policy_id`, `content_sha256`, 가공기 버전을 참조해야 한다.
- 저장 루트와 실제 정책 원문은 Git에 커밋하지 않는다. 테스트에는 비민감 합성 샘플만 사용한다.

## 개인정보 미수집 기준

정책 수집은 공개 정책 문서만 대상으로 하며 정책 이해에 필요하지 않은 개인정보를 수집하지 않는다.

- 신청자 이름, 연락처, 이메일, 상세 주소, 주민등록번호, 계좌번호, 신청서와 첨부 증빙을 수집하지 않는다.
- 로그인 세션, cookie, Authorization header, API key, 서명 URL을 보관하지 않는다.
- 공개 문서에 담당자 업무 연락처가 포함된 경우 원본의 무결성을 위해 Raw 바이트는 그대로 보존할 수 있으나, Processed 텍스트·검색 청크·LLM 입력에서는 정책 근거에 불필요한 연락처를 제거한다.
- 개인정보가 포함된 신청 목록, 선정 결과 명단, 민원·사례 페이지는 수집 대상에서 제외하고 `REJECTED` 처리한다.
- 발견된 개인정보 값을 로그, 오류 메시지, 파일명 또는 메타데이터에 복제하지 않는다.

## 무결성 검증

원문을 읽은 exact bytes로 SHA-256을 계산한 뒤 파일을 저장하고, sidecar의 `content_sha256`과 다시 비교한다. HTML 정리, PDF 텍스트 추출, 문자 인코딩 변환 후의 값은 별도 Processed 산출물이며 원문 해시가 아니다.
