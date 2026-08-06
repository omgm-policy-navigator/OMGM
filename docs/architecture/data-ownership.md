# 데이터 소유권

## 사용자 계정 영역

소유 데이터: 사용자 식별자, 인증 정보, 약관 동의, 개인정보 동의, 계정 상태.

변경 책임: 인증·계정 모듈. Phase 0에는 구현하지 않는다.

조회 허용 범위: 본인, 최소 권한을 가진 운영 역할.

## 사용자 프로필 및 답변 영역

소유 데이터: 혼인 상태, 혼인신고일, 거주 지역, 세대 정보, 소득 정보, 자산 정보, 주택 소유 여부, 답변 확정 여부, 답변 출처, 답변 변경 이력.

변경 책임: 사용자 답변 수집 모듈. 실제 수집 필드는 확정 설계와 동의 범위에 한정한다.

조회 허용 범위: 판정 모듈은 필요한 필드만 조회한다. 설명 모듈은 화면에 필요한 값만 받는다.

## 정책 기준 데이터 영역

소유 데이터: 검수된 정책, 질문, Rule, 정책 관계, RAG 문서 CSV.

변경 책임: 저장소 코드 리뷰를 거친 `backend/data/policy-seed` 변경.

조회 허용 범위: Backend Policy Module이 시작 시 읽고 검증한다. 런타임에 파일을 수정하지 않는다.

D0 Raw Policy Schema는 과거 수집 파이프라인 계약으로 보존한다. 현재 MVP 실행 경로는 제공·검수된 CSV 기준본이며 `source_url`이 없는 데이터는 로딩하지 않는다. 변동 기준 placeholder는 공식 확인 전 확정 판정 근거로 사용할 수 없다.

D4 가공 Chunk는 정책 기준 데이터 영역이 소유한다. 각 Chunk는 `policy_id`, `document_id`, 문서·의미 유형, 제목, 원문 URL, 원문 위치, 품질 상태, 콘텐츠 SHA-256을 가진다. `APPROVED` Chunk만 임베딩 입력 Seed로 노출하며 API 요청 중 Chunk CSV를 변경하지 않는다.

## 게시 정책 영역

소유 데이터: 승인·게시된 정책 식별자, 정책명, 기관, 지역, 대상, 신청 기간, 정책 상태, `policy_version`, 승인된 `policy_rule`, 승인된 `policy_document`, 서비스 조회용 Read Model.

변경 책임: Backend Policy Module. 검수 완료 CSV를 읽기 전용 게시 기준으로 반영한다.

조회 허용 범위: 정책 검색, 구조화, 판정, 설명 모듈.

## 정책 조건 영역

소유 데이터: 조건 식별자, 조건 유형, 비교 연산자, 기준값, 단위, 필수 여부, 원문 근거 위치, 구조화 검증 상태, 적용 `policy_version`.

변경 책임: 정책 구조화 모듈과 검증 흐름.

조회 허용 범위: 판정 모듈은 검증된 조건만 확정 판정에 사용한다.

## 판정 영역

소유 데이터: 판정 식별자, 사용자 또는 서버 발급 익명 세션 식별자, 정책 식별자, `policy_version`, 사용자 정보 버전, eligibility status, evaluation state, 충족 조건, 불충족 조건, 미확인 조건, 판정 근거.

변경 책임: 자격판정 모듈.

조회 허용 범위: 결과 설명 모듈, 사용자 본인, 필요한 운영 역할.

## 대화 및 질문 영역

소유 데이터: 대화 세션, 질문, 사용자 답변, 정규화 결과, 충돌 여부, 추가 확인 요청.

변경 책임: 사용자 정보 수집 모듈.

보존 기준: 기획에 영구 저장 요구가 없는 한 대화 전문을 무기한 저장하지 않는다.

## 버전과 감사

사용자 답변, 정책, 정책 조건, 판정은 각각 버전을 가져야 한다. 변경 전후 값과 변경 시점을 추적해 정책 변경과 답변 충돌의 영향을 감사할 수 있어야 한다.

## 삭제 및 보존

개인정보와 민감정보의 보존 기간은 미확정이다. 다음 Phase에서 동의 목적, 법적 근거, 서비스 필요성을 기준으로 필드별 보존 기간을 확정해야 한다.

AI A2 조건 추출 결과는 사용자 사실 저장값이 아니라 후보 DTO다. 낮은 신뢰도, 모호성, 기존 확정 사실과의 충돌이 있으면 재확인 전까지 확정하거나 저장하지 않는다. A2 자체는 `user_fact` 테이블을 만들거나 변경하지 않는다.
## D6 change candidate ownership

- Official HTTP responses collected by D6 are transient candidate inputs, not the active policy catalog.
- `ReviewReport` owns hashes, field changes, affected Rule/Chunk IDs, required reindex/reevaluation actions, and review
  attribution. It deliberately excludes raw response bytes and credentials, and persisted report files are append-only.
- The committed `backend/data/policy-seed` remains the only reviewed runtime baseline.
- Approved regeneration output is a separate staged Seed directory. Promotion to the committed baseline remains an
  explicit administrator review and Git change; D6 does not publish to PostgreSQL automatically.
