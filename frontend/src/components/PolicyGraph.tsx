import { Background, Handle, ReactFlow, type Edge, type Node, type NodeProps, Position } from "@xyflow/react";
import { X } from "lucide-react";
import { useMemo, useState } from "react";
import type { PolicyNodeData } from "../data/policies";
import { policyNodes } from "../data/policies";

type GraphNodeData = PolicyNodeData & {
  variant: "central" | "policy";
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

export function PolicyGraph() {
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyNodeData | null>(null);

  const { nodes, edges } = useMemo(() => {
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
        stroke: "rgba(111, 167, 126, 0.62)",
        strokeWidth: 0.75,
      }),
    );

    return { nodes: [center, ...policyGraphNodes], edges: radialEdges };
  }, []);

  return (
    <section className="relative flex h-full min-w-0 flex-col overflow-hidden rounded-3xl border border-brand-border bg-white shadow-card" aria-label="맞춤 정책 그래프">
      <header className="z-10 border-b border-brand-border bg-white/90 p-6 backdrop-blur">
        <h2 className="text-h3">맞춤 정책 그래프</h2>
        <p className="mt-1 text-body-sm text-text-secondary">정책 노드를 클릭하면 자격 근거와 다음 단계를 확인할 수 있어요.</p>
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
            if (data.variant === "policy") {
              setSelectedPolicy(data);
            }
          }}
        >
          <Background color="#B8D8C1" gap={32} size={1} />
        </ReactFlow>
      </div>

      {selectedPolicy && <PolicyModal policy={selectedPolicy} onClose={() => setSelectedPolicy(null)} />}
    </section>
  );
}

function PolicyNode({ data }: NodeProps<Node<GraphNodeData>>) {
  const Icon = data.icon;
  const isCentral = data.variant === "central";

  return (
    <div
      className={`relative flex flex-col items-center justify-center rounded-full text-center shadow-card ${
        isCentral
          ? "h-[120px] w-[120px] border-2 border-brand-primary bg-white text-text-primary"
          : "h-[100px] w-[100px] cursor-pointer border border-brand-border bg-brand-surface text-text-primary transition hover:-translate-y-1 hover:border-brand-primary hover:bg-brand-surface-container"
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

function PolicyModal({ policy, onClose }: { policy: PolicyNodeData; onClose: () => void }) {
  const Icon = policy.icon;

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
              <p className="text-caption text-brand-primary">Policy Detail</p>
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
            <h4 className="text-h4">확인된 조건</h4>
            <ul className="mt-3 space-y-2 text-body-sm text-text-secondary">
              <li>서울 거주 또는 전입 예정</li>
              <li>예비부부 또는 신혼부부</li>
              <li>무주택 여부 확인 완료</li>
              <li>소득 구간 추가 확인 필요</li>
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
