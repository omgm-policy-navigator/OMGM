const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function App() {
  return (
    <main className="shell">
      <section className="workspace" aria-label="정책 탐색 작업 영역">
        <aside className="panel">
          <h1>나만 결혼해?</h1>
          <p>결혼·신혼부부 지원정책을 조건과 근거 중심으로 확인합니다.</p>
          <div className="status">Backend: {apiBaseUrl}</div>
        </aside>
        <section className="chat" aria-label="챗봇 패널">
          <div className="message">혼인 상태, 거주지, 소득처럼 판정에 필요한 정보를 차례로 확인합니다.</div>
          <button type="button">정책 탐색 시작</button>
        </section>
        <section className="summary" aria-label="정책 근거">
          <h2>판정 결과</h2>
          <ul>
            <li>정보 부족은 확인 필요로 분리</li>
            <li>정책 원문과 버전 연결</li>
            <li>최종 심사는 행정기관 기준</li>
          </ul>
        </section>
      </section>
    </main>
  );
}
