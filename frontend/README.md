# Frontend

React Web 사용자 인터페이스입니다. 챗봇 패널, 정책 그래프, 정책 상세, 내 정책, 저장 정책, 알림 상태, 확인이 필요한 사용자 정보 입력, 판정 결과와 정책 근거 확인 화면으로 확장합니다.

## 실행

```bash
cd frontend
npm install
npm run dev
```

## 테스트와 빌드

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

## 환경변수

루트 `.env.example`의 `VITE_API_BASE_URL`, `VITE_SSE_BASE_URL`을 사용합니다. 브라우저에 노출되므로 서버 Secret을 `VITE_*` 변수에 넣지 않습니다.
