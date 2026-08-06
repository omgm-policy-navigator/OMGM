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

function iconForBackendNode(node: SessionGraphNode) {
  if (node.type === "user") {
    return UserRound;
  }
  if (node.type === "category") {
    const categoryCode = typeof node.data.categoryCode === "string" ? node.data.categoryCode : "";
    const category = categories.find(({ backendCategoryCode }) => backendCategoryCode === categoryCode);
    return category?.icon ?? FolderTree;
  }
  if (node.type === "policy") {
    return Landmark;
  }
  if (node.type === "condition") {
    return ListChecks;
  }
  if (node.type === "action") {
    return FileCheck2;
  }
  return CircleHelp;
}

function variantForBackendNode(type: string): GraphNodeData["variant"] {
  if (type === "user") {
    return "central";
  }
  if (type === "category") {
    return "category";
  }
  if (type === "condition") {
    return "condition";
  }
  if (type === "action") {
    return "action";
  }
  return "policy";
}

function descriptionForBackendNode(node: SessionGraphNode) {
  if (typeof node.data.description === "string") {
    return node.data.description;
  }
  if (node.type === "policy") {
    const status = typeof node.data.eligibilityStatus === "string" ? `자격 상태: ${node.data.eligibilityStatus}` : "세션 답변을 기준으로 평가된 정책입니다.";
    const score = typeof node.data.recommendationScore === "number" ? `추천 점수: ${node.data.recommendationScore}` : null;
    return [status, score].filter(Boolean).join(" / ");
  }
  if (node.type === "condition") {
    const factKey = typeof node.data.factKey === "string" ? node.data.factKey : "condition";
    return `확인 조건: ${factKey}`;
  }
  return "백엔드 세션 그래프에서 전달된 노드입니다.";
}

function statusForBackendNode(node: SessionGraphNode): PolicyNodeData["status"] {
  if (node.type !== "policy") {
    return "recommended";
  }
  if (node.data.eligibilityStatus === "eligible") {
    return "eligible";
  }
  if (node.data.evaluationState === "complete") {
    return "recommended";
  }
  return "checking";
}

export function PolicyGraph({ selectedCategoryId, sessionGraph }: PolicyGraphProps) {
  const [selectedPolicy, setSelectedPolicy] = useState<GraphNodeData | null>(null);

  const { nodes, edges } = useMemo(() => {
    if (sessionGraph && sessionGraph.nodes.length > 0) {
      const centerIndex = sessionGraph.nodes.findIndex((node) => node.type === "user");
      const orderedNodes = centerIndex >= 0 ? [sessionGraph.nodes[centerIndex], ...sessionGraph.nodes.filter((_, index) => index !== centerIndex)] : sessionGraph.nodes;
      const center: GraphPoint = { x: 350, y: 250 };
      const radius = 230;
      const liveNodes: Node<GraphNodeData>[] = orderedNodes.map((graphNode, index) => {
        const isCenter = index === 0 && graphNode.type === "user";
        const angle = (Math.PI * 2 * Math.max(index - 1, 0)) / Math.max(orderedNodes.length - 1, 1) - Math.PI / 2;
        return {
          id: graphNode.id,
          type: "policyNode",
          position: isCenter
            ? center
            : {
                x: center.x + Math.cos(angle) * radius,
                y: center.y + Math.sin(angle) * radius,
              },
          data: {
            id: graphNode.id,
            label: graphNode.label,
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
            style: {
              stroke: designTokens.color.graph.edge,
              strokeWidth: 0.85,
            },
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
          {sessionGraph ? `${selectedCategory.label} 세션 그래프 ${sessionGraph.nodeCount}개 노드를 표시합니다.` : "정책 노드를 클릭하면 자격 근거와 다음 단계를 확인할 수 있어요."}
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

  return (
    <div
      className={`relative flex flex-col items-center justify-center rounded-full text-center shadow-card ${
        isCentral
          ? "h-[120px] w-[120px] border-2 border-brand-primary bg-white text-text-primary"
          : `h-[100px] w-[100px] cursor-pointer border border-brand-border text-text-primary transition hover:-translate-y-1 hover:border-brand-primary hover:bg-brand-surface-container ${
              isPolicy ? "bg-brand-surface" : "bg-white"
            }`
      }`}
    >
      {handlePositions.map(({ id, position }) => (
        <Handle key={`target-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="target" position={position} />
      ))}
      {handlePositions.map(({ id, position }) => (
        <Handle key={`source-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="source" position={position} />
      ))}
      <Icon size={isCentral ? 30 : 24} className="mb-2 text-brand-primary" />
      <span className={`${isCentral ? "text-caption" : "px-2 text-[11px] font-medium leading-4"}`}>{data.label}</span>
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
