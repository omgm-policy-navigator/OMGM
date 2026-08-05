import { useHealthQuery } from "./api/useHealthQuery";

export function HealthStatusPanel() {
  const healthQuery = useHealthQuery();

  if (healthQuery.isPending) {
    return (
      <aside className="health-card" aria-label="백엔드 상태">
        <span className="health-label">Health</span>
        <strong>확인 중</strong>
      </aside>
    );
  }

  if (healthQuery.isError) {
    return (
      <aside className="health-card health-card-error" aria-label="백엔드 상태">
        <span className="health-label">Health</span>
        <strong>확인 실패</strong>
        <p>Mock 또는 API 응답을 불러오지 못했습니다.</p>
      </aside>
    );
  }

  const health = healthQuery.data;

  return (
    <aside className="health-card" aria-label="백엔드 상태">
      <span className="health-label">Health</span>
      <strong>{health.status}</strong>
      <p>
        {health.service} · {health.environment}
      </p>
    </aside>
  );
}
