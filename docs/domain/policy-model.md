# 정책 모델

## 개념 모델

Phase 0에서는 실제 테이블이나 영속 모델을 확정하지 않는다. 다음 개념은 향후 구현 계약이다.

## Policy

- 정책 식별자.
- 정책명.
- 제공기관.
- 지역.
- 대상.
- 신청 기간.
- 필요 서류.
- 정책 상태.
- 현재 `policy_version`.

## Policy Version

- 정책 버전 식별자.
- 정책 식별자.
- 버전 문자열 또는 게시 번호.
- 적용 시작일.
- 적용 종료일.
- 게시 상태.
- 원문 해시.

## Policy Source

- 원문 URL.
- 원문 본문 또는 보관 위치.
- 수집 시점.
- 원문 해시.
- 출처 기관.
- 연결된 `policy_version`.

정책 원문은 공개 데이터일 수 있으나 수집 시점과 원문 해시를 기록해 변경을 감지해야 한다.

## Policy Condition

- 조건 식별자.
- 조건 유형.
- 비교 연산자.
- 기준값.
- 단위.
- 필수 여부.
- 원문 근거 위치.
- 구조화 검증 상태.
- 적용 `policy_version`.

LLM으로 추출한 조건 후보는 검증 전까지 확정 판정 규칙으로 취급하지 않는다.

## 정책 버전

정책 원문, 구조화 조건, 판정 규칙 중 하나라도 변경되면 판정에 영향을 줄 수 있다. 판정은 사용한 `policy_version`을 항상 기록해야 한다.

## 변경 탐지

최소 변경 탐지 값은 원문 해시다. D0에서 원문 해시는 수집해 보존한 exact bytes 전체의 SHA-256으로 확정했다. URL별 수집 주기와 구조화 조건 diff 기준은 후속 Phase에서 정한다. Raw 메타데이터와 저장 기준은 [Raw Policy Schema](../data/raw-policy-schema.md)를 따른다.

## Phase B2 Policy Catalog Implementation

The B2 catalog implementation stores policy metadata directly in `policy` and links it to `category`. Public catalog APIs return DTOs, not ORM entities. The first seed set contains twelve approved active policies and one inactive draft policy used to verify that non-approved data is not publicly exposed.

Policy detail responses include agency, region, application period, support type, and official source metadata with `reviewedAt`. Document responses include official source, reviewed date, collection timestamp, and hash metadata.