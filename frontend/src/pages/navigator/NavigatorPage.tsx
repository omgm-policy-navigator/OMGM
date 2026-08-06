import { HealthStatusPanel } from "@/features/health";
import { AppShell } from "@/shared/ui";

export function NavigatorPage() {
  return (
    <AppShell>
      <section className="hero-panel" aria-labelledby="navigator-title">
        <div>
          <p className="eyebrow">OMGM Policy Navigator</p>
          <h1 id="navigator-title">나만 결혼 혜택?</h1>
          <p className="lede">결혼·신혼부부 지원정책을 조건과 근거 중심으로 확인합니다.</p>
        </div>
        <HealthStatusPanel />
      </section>

      <section className="workspace" aria-label="정책 탐색 작업 영역">
        <section className="panel panel-chat" aria-label="챗봇 패널">
          <h2>챗봇</h2>
          <p>혼인 상태, 거주지, 소득처럼 판정에 필요한 정보를 차례로 확인합니다.</p>
          <button type="button">정책 탐색 시작</button>
        </section>

        <section className="panel panel-graph" aria-label="정책 그래프 패널">
          <h2>정책 그래프</h2>
          <p>정책, 조건, 질문, 근거의 연결 구조를 이 영역에서 표시합니다.</p>
        </section>

        <section className="panel panel-detail" aria-label="정책 상세 패널">
          <h2>정책 상세</h2>
          <ul>
            <li>정보 부족은 확인 필요로 분리</li>
            <li>정책 원문과 버전 연결</li>
            <li>최종 심사는 행정기관 기준</li>
          </ul>
        </section>
      </section>
    </AppShell>
  );
}
