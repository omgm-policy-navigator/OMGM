import { Background, Handle, ReactFlow, type Edge, type Node, type NodeProps, Position } from "@xyflow/react";
import { CircleHelp, FileCheck2, FolderTree, Landmark, ListChecks, UserRound, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { PolicyNodeData } from "../data/policies";
import { categories, policyNodes } from "../data/policies";
import { designTokens } from "../design";
import type { SessionGraphNode, SessionGraphResponse } from "../shared/api/chatbot";

type GraphNodeData = PolicyNodeData & {
  variant: "central" | "policy" | "condition" | "category" | "action";
  backendType?: string;
  backendData?: Record<string, unknown>;
};

type GraphPoint = {
  x: number;
  y: number;
};

type BackendNodeType = "USER" | "CATEGORY" | "POLICY" | "CONDITION" | "ACTION";

const nodeTypes = {
  policyNode: PolicyNode,
};

const handlePositions = [
  { id: "top", position: Position.Top },
  { id: "right", position: Position.Right },
  { id: "bottom", position: Position.Bottom },
  { id: "left", position: Position.Left },
] as const;

function getClosestHandle(from: GraphPoint, to: GraphPoint) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;

  if (Math.abs(dx) > Math.abs(dy)) {
    return dx > 0 ? "right" : "left";
  }

  return dy > 0 ? "bottom" : "top";
}

function getOppositeHandle(handle: string) {
  const opposites: Record<string, string> = {
    top: "bottom",
    right: "left",
    bottom: "top",
    left: "right",
  };

  return opposites[handle];
}

type PolicyGraphProps = {
  selectedCategoryId: string;
  sessionGraph: SessionGraphResponse | null;
};

const factLabels: Record<string, string> = {
  region: "거주 지역",
  marital_status: "혼인 상태",
  household_income_range: "소득 구간",
  housing_status: "주택 보유",
  lease_type: "계약 유형",
  marriage_registered: "혼인신고",
  marriage_registration_date: "혼인신고일",
  loan_purpose: "대출 목적",
  pregnancy_status: "임신/출산",
  has_child: "자녀 여부",
  child_age_months: "자녀 개월 수",
  education_topic: "상담 주제",
};

const valueLabels: Record<string, string> = {
  Seoul: "서울",
  Gyeonggi: "경기",
  Incheon: "인천",
  Busan: "부산",
  National: "전국",
  engaged: "예비부부",
  newlywed: "신혼부부",
  married: "기혼",
  single: "미혼",
  unknown: "미확인",
  under_50m: "5천만 미만",
  "50m_to_80m": "5천만-8천만",
  "80m_to_120m": "8천만-1억2천",
  over_120m: "1억2천 초과",
  no_home: "무주택",
  own_home: "주택 소유",
  jeonse: "전세",
  monthly_rent: "월세",
  purchase: "매매",
  true: "예",
  false: "아니오",
  housing: "주거",
  wedding: "웨딩",
  settlement: "정착",
};

function normalizeBackendType(type: string): BackendNodeType | "UNKNOWN" {
  const normalized = type.toUpperCase();
  if (normalized === "USER" || normalized === "CATEGORY" || normalized === "POLICY" || normalized === "CONDITION" || normalized === "ACTION") {
    return normalized;
  }
  return "UNKNOWN";
}

function labelValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "미확인";
  }
  if (typeof value === "boolean") {
    return value ? "예" : "아니오";
  }
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string") {
    return valueLabels[value] ?? value;
  }
  return JSON.stringify(value);
}

function categoryLabel(categoryCode: unknown, fallback: string) {
  if (typeof categoryCode !== "string") {
    return fallback;
  }
  return categories.find(({ backendCategoryCode }) => backendCategoryCode === categoryCode)?.label ?? fallback;
}

function displayLabelForBackendNode(node: SessionGraphNode) {
  const type = normalizeBackendType(node.type);
  if (type === "USER") {
    return "우리 부부";
  }
  if (type === "CATEGORY") {
    return categoryLabel(node.data.categoryCode, node.label);
  }
  if (type === "CONDITION") {
    const factKey = typeof node.data.factKey === "string" ? node.data.factKey : node.label;
    const factLabel = factLabels[factKey] ?? factKey;
    return node.data.value === undefined ? factLabel : `${factLabel}\n${labelValue(node.data.value)}`;
  }
  if (type === "ACTION") {
    return "신청 단계 확인";
  }
  return node.label;
}

function iconForBackendNode(node: SessionGraphNode) {
  const type = normalizeBackendType(node.type);
  if (type === "USER") {
    return UserRound;
  }
  if (type === "CATEGORY") {
    const categoryCode = typeof node.data.categoryCode === "string" ? node.data.categoryCode : "";
    const category = categories.find(({ backendCategoryCode }) => backendCategoryCode === categoryCode);
    return category?.icon ?? FolderTree;
  }
  if (type === "POLICY") {
    return Landmark;
  }
  if (type === "CONDITION") {
    return ListChecks;
  }
  if (type === "ACTION") {
    return FileCheck2;
  }
  return CircleHelp;
}

function variantForBackendNode(type: string): GraphNodeData["variant"] {
  const normalized = normalizeBackendType(type);
  if (normalized === "USER") {
    return "central";
  }
  if (normalized === "CATEGORY") {
    return "category";
  }
  if (normalized === "CONDITION") {
    return "condition";
  }
  if (normalized === "ACTION") {
    return "action";
  }
  return "policy";
}

function descriptionForBackendNode(node: SessionGraphNode) {
  if (typeof node.data.description === "string") {
    return node.data.description;
  }
  const type = normalizeBackendType(node.type);
  if (type === "POLICY") {
    const status = typeof node.data.eligibilityStatus === "string" ? `자격 상태: ${node.data.eligibilityStatus}` : "세션 답변을 기준으로 평가된 정책입니다.";
    const score = typeof node.data.recommendationScore === "number" ? `추천 점수: ${node.data.recommendationScore}` : null;
    return [status, score].filter(Boolean).join(" / ");
  }
  if (type === "CONDITION") {
    const factKey = typeof node.data.factKey === "string" ? node.data.factKey : "condition";
    const factLabel = factLabels[factKey] ?? factKey;
    return `확인 조건: ${factLabel}`;
  }
  return "백엔드 세션 그래프에서 전달된 노드입니다.";
}

function statusForBackendNode(node: SessionGraphNode): PolicyNodeData["status"] {
  if (normalizeBackendType(node.type) !== "POLICY") {
    return "recommended";
  }
  if (node.data.eligibilityStatus === "LIKELY_ELIGIBLE" || node.data.eligibilityStatus === "eligible") {
    return "eligible";
  }
  if (node.data.evaluationState === "ACTIVE" || node.data.evaluationState === "complete") {
    return "recommended";
  }
  return "checking";
}

function spreadY(index: number, total: number, centerY: number, spacing: number) {
  return centerY + (index - (total - 1) / 2) * spacing;
}

function countNodesByType(nodes: SessionGraphNode[]) {
  return nodes.reduce((counts, node) => {
    const type = normalizeBackendType(node.type);
    counts.set(type, (counts.get(type) ?? 0) + 1);
    return counts;
  }, new Map<BackendNodeType | "UNKNOWN", number>());
}

function layoutLiveNode(graphNode: SessionGraphNode, index: number, total: number): GraphPoint {
  const type = normalizeBackendType(graphNode.type);

  if (type === "USER") {
    return { x: 80, y: 280 };
  }
  if (type === "CATEGORY") {
    return { x: 280, y: 280 };
  }
  if (type === "POLICY") {
    return { x: 520, y: spreadY(index, total, 250, 120) };
  }
  if (type === "CONDITION") {
    return { x: 280, y: spreadY(index, total, 500, 88) };
  }
  if (type === "ACTION") {
    return { x: 780, y: spreadY(index, total, 250, 120) };
  }
  return { x: 520, y: spreadY(index, total, 500, 96) };
}

function edgeStyleForType(edgeType: string): Edge["style"] {
  if (edgeType === "MATCHES") {
    return { stroke: designTokens.color.graph.edge, strokeWidth: 1.6 };
  }
  if (edgeType === "MISSING_CONDITION") {
    return { stroke: "#D99B2B", strokeDasharray: "6 5", strokeWidth: 1.4 };
  }
  if (edgeType === "FAILED_CONDITION") {
    return { stroke: "#C05A4B", strokeDasharray: "4 4", strokeWidth: 1.4 };
  }
  if (edgeType === "NEXT_ACTION") {
    return { stroke: "#5F9F73", strokeDasharray: "8 5", strokeWidth: 1.4 };
  }
  return { stroke: designTokens.color.graph.edge, strokeWidth: 1 };
}

export function PolicyGraph({ selectedCategoryId, sessionGraph }: PolicyGraphProps) {
  const [selectedPolicy, setSelectedPolicy] = useState<GraphNodeData | null>(null);

  const { nodes, edges } = useMemo(() => {
    if (sessionGraph && sessionGraph.nodes.length > 0) {
      const totalByType = countNodesByType(sessionGraph.nodes);
      const indexByType = new Map<BackendNodeType | "UNKNOWN", number>();
      const liveNodes: Node<GraphNodeData>[] = sessionGraph.nodes.map((graphNode) => {
        const type = normalizeBackendType(graphNode.type);
        const typeIndex = indexByType.get(type) ?? 0;
        indexByType.set(type, typeIndex + 1);
        return {
          id: graphNode.id,
          type: "policyNode",
          position: layoutLiveNode(graphNode, typeIndex, totalByType.get(type) ?? 1),
          data: {
            id: graphNode.id,
            label: displayLabelForBackendNode(graphNode),
            description: descriptionForBackendNode(graphNode),
            icon: iconForBackendNode(graphNode),
            status: statusForBackendNode(graphNode),
            variant: variantForBackendNode(graphNode.type),
            backendType: graphNode.type,
            backendData: graphNode.data,
          },
        };
      });
      const graphNodePositions = new Map<string, GraphPoint>(liveNodes.map((node) => [node.id, node.position]));
      const visibleNodeIds = new Set(liveNodes.map(({ id }) => id));
      const liveEdges: Edge[] = sessionGraph.edges
        .filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))
        .map((edge) => {
          const sourcePosition = graphNodePositions.get(edge.source);
          const targetPosition = graphNodePositions.get(edge.target);
          const sourceHandle = sourcePosition && targetPosition ? getClosestHandle(sourcePosition, targetPosition) : "right";
          return {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            sourceHandle,
            targetHandle: getOppositeHandle(sourceHandle),
            type: "straight",
            animated: false,
            style: edgeStyleForType(edge.type),
          };
        });

      return { nodes: liveNodes, edges: liveEdges };
    }

    const center: Node<GraphNodeData> = {
      id: "couple",
      type: "policyNode",
      position: { x: 350, y: 250 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: {
        id: "couple",
        label: "우리 부부",
        description: "현재 답변한 조건을 기준으로 정책 연결을 계산합니다.",
        icon: policyNodes[5].icon,
        status: "recommended",
        variant: "central",
      },
    };

    const radius = 230;
    const policyGraphNodes: Node<GraphNodeData>[] = policyNodes.map((policy, index) => {
      const angle = (Math.PI * 2 * index) / policyNodes.length - Math.PI / 2;
      return {
        id: policy.id,
        type: "policyNode",
        position: {
          x: 350 + Math.cos(angle) * radius,
          y: 250 + Math.sin(angle) * radius,
        },
        data: { ...policy, variant: "policy" },
      };
    });

    const graphNodePositions = new Map<string, GraphPoint>([center, ...policyGraphNodes].map((node) => [node.id, node.position]));

    const createEdge = (source: string, target: string, style: Edge["style"]): Edge => {
      const sourcePosition = graphNodePositions.get(source);
      const targetPosition = graphNodePositions.get(target);
      const sourceHandle = sourcePosition && targetPosition ? getClosestHandle(sourcePosition, targetPosition) : "right";

      return {
        id: `${source}-${target}`,
        source,
        target,
        sourceHandle,
        targetHandle: getOppositeHandle(sourceHandle),
        type: "straight",
        animated: false,
        style,
      };
    };

    const radialEdges: Edge[] = policyNodes.map((policy) =>
      createEdge("couple", policy.id, {
        stroke: designTokens.color.graph.edge,
        strokeWidth: 0.75,
      }),
    );

    return { nodes: [center, ...policyGraphNodes], edges: radialEdges };
  }, [sessionGraph]);

  const selectedCategory = categories.find(({ id }) => id === selectedCategoryId) ?? categories[0];

  return (
    <section className="relative flex h-full min-w-0 flex-col overflow-hidden rounded-3xl border border-brand-border bg-white shadow-card" aria-label="맞춤 정책 그래프">
      <header className="z-10 border-b border-brand-border bg-white/90 p-6 backdrop-blur">
        <h2 className="text-h3">맞춤 정책 그래프</h2>
        <p className="mt-1 text-body-sm text-text-secondary">
          {sessionGraph ? `${selectedCategory.label} 정책과 확인 조건을 연결해 표시합니다.` : "정책 노드를 클릭하면 자격 근거와 다음 단계를 확인할 수 있어요."}
        </p>
      </header>

      <div className="policy-graph-bg h-full min-h-[560px] flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.55}
          maxZoom={1.4}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          edgesFocusable={false}
          nodesFocusable={false}
          panOnScroll={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          preventScrolling
          onNodeClick={(_, node) => {
            const data = node.data;
            if (data.variant !== "central") {
              setSelectedPolicy(data);
            }
          }}
        >
          <Background color={designTokens.color.graph.backgroundLine} gap={32} size={1} />
        </ReactFlow>
      </div>

      {selectedPolicy && <PolicyModal policy={selectedPolicy} onClose={() => setSelectedPolicy(null)} />}
    </section>
  );
}

function PolicyNode({ data }: NodeProps<Node<GraphNodeData>>) {
  const Icon = data.icon;
  const isCentral = data.variant === "central";
  const isPolicy = data.variant === "policy";
  const isCondition = data.variant === "condition";
  const isAction = data.variant === "action";

  return (
    <div
      className={`relative flex text-center shadow-card ${
        isCentral
          ? "h-[112px] w-[112px] flex-col items-center justify-center rounded-full border-2 border-brand-primary bg-white text-text-primary"
          : `min-h-[72px] cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 text-left text-text-primary transition hover:-translate-y-1 hover:border-brand-primary hover:bg-brand-surface-container ${
              isPolicy
                ? "w-[178px] border-brand-primary bg-brand-surface"
                : isCondition
                  ? "w-[148px] border-brand-border bg-white"
                  : isAction
                    ? "w-[150px] border-brand-border bg-brand-surface-container"
                    : "w-[142px] border-brand-border bg-white"
            }`
      }`}
    >
      {handlePositions.map(({ id, position }) => (
        <Handle key={`target-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="target" position={position} />
      ))}
      {handlePositions.map(({ id, position }) => (
        <Handle key={`source-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="source" position={position} />
      ))}
      <Icon size={isCentral ? 30 : 22} className={`${isCentral ? "mb-2" : "shrink-0"} text-brand-primary`} />
      <span className={`${isCentral ? "text-caption" : "whitespace-pre-line text-[12px] font-medium leading-4"}`}>{data.label}</span>
    </div>
  );
}

function formatBackendValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "미확인";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function visibleBackendEntries(data: Record<string, unknown> | undefined) {
  if (!data) {
    return [];
  }
  return Object.entries(data).filter(([key]) => ["eligibilityStatus", "evaluationState", "recommendationScore", "factKey", "value", "categoryCode"].includes(key));
}

function PolicyModal({ policy, onClose }: { policy: GraphNodeData; onClose: () => void }) {
  const Icon = policy.icon;
  const backendEntries = visibleBackendEntries(policy.backendData);

  return (
    <>
      <div className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-[4px] brightness-95" onClick={onClose} />
      <article className="fixed left-1/2 top-1/2 z-[101] max-h-[80vh] w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 scale-100 overflow-hidden rounded-3xl bg-white opacity-100 shadow-card animate-modal-in">
        <header className="flex items-start justify-between gap-4 border-b border-brand-border bg-brand-surface p-6">
          <div className="flex gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-primary text-white">
              <Icon size={24} />
            </div>
            <div>
              <p className="text-caption text-brand-primary">{policy.backendType ? `${policy.backendType} Detail` : "Policy Detail"}</p>
              <h3 className="mt-1 text-h3">{policy.label}</h3>
            </div>
          </div>
          <button type="button" onClick={onClose} className="flex h-10 w-10 items-center justify-center rounded-xl text-text-secondary transition hover:bg-white">
            <X size={20} />
          </button>
        </header>
        <div className="space-y-5 overflow-y-auto p-6">
          <p className="text-body-md text-text-secondary">{policy.description}</p>
          <div className="rounded-xl border border-brand-border bg-white p-4">
            <h4 className="text-h4">{backendEntries.length > 0 ? "백엔드 그래프 데이터" : "확인된 조건"}</h4>
            <ul className="mt-3 space-y-2 text-body-sm text-text-secondary">
              {backendEntries.length > 0 ? (
                backendEntries.map(([key, value]) => (
                  <li key={key}>
                    {key}: {formatBackendValue(value)}
                  </li>
                ))
              ) : (
                <>
                  <li>서울 거주 또는 전입 예정</li>
                  <li>예비부부 또는 신혼부부</li>
                  <li>무주택 여부 확인 완료</li>
                  <li>소득 구간 추가 확인 필요</li>
                </>
              )}
            </ul>
          </div>
          <button type="button" className="h-12 w-full rounded-xl bg-brand-primary text-body-md text-white transition duration-200 hover:brightness-90 active:scale-95">
            신청 일정과 제출 서류 보기
          </button>
        </div>
      </article>
    </>
  );
}
