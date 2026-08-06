import { Background, Controls, Handle, ReactFlow, type Edge, type Node, type NodeProps, Position } from "@xyflow/react";
import { CircleHelp, ExternalLink, FileCheck2, FolderTree, Landmark, ListChecks, UserRound, UsersRound, X } from "lucide-react";
import type { CSSProperties, PointerEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import type { PolicyNodeData } from "../data/policies";
import { categories, policyNodes } from "../data/policies";
import { designTokens } from "../design";
import {
  getPolicyDetail,
  listCategoryPolicies,
  type PolicyDetailResponse,
  type PolicySummaryResponse,
  type SessionGraphNode,
  type SessionGraphResponse,
} from "../shared/api/chatbot";

type GraphNodeData = PolicyNodeData & {
  variant: "central" | "policy" | "condition" | "category" | "action" | "detail";
  backendType?: string;
  backendData?: Record<string, unknown>;
  tone?: "positive" | "negative" | "neutral";
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

const eligibleStatuses = new Set(["LIKELY_ELIGIBLE", "eligible", "ELIGIBLE"]);
const ineligibleStatuses = new Set(["LIKELY_INELIGIBLE", "INELIGIBLE", "ineligible"]);

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
    return "신청 방법";
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
    return "detail";
  }
  return "policy";
}

function descriptionForBackendNode(node: SessionGraphNode) {
  if (typeof node.data.description === "string") {
    return node.data.description;
  }
  const type = normalizeBackendType(node.type);
  if (type === "POLICY") {
    return typeof node.data.eligibilityStatus === "string" ? eligibilityStatusLabel(node.data.eligibilityStatus) : "세션 답변을 기준으로 평가된 정책입니다.";
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

function eligibilityStatusValue(node: SessionGraphNode | undefined) {
  const status = node?.data.eligibilityStatus;
  return typeof status === "string" ? status : "";
}

function policyToneForBackendNode(node: SessionGraphNode): GraphNodeData["tone"] {
  if (normalizeBackendType(node.type) !== "POLICY") {
    return "neutral";
  }
  const status = eligibilityStatusValue(node);
  if (eligibleStatuses.has(status)) {
    return "positive";
  }
  if (ineligibleStatuses.has(status)) {
    return "negative";
  }
  return "neutral";
}

function conditionToneForNode(nodeId: string, edges: SessionGraphResponse["edges"]): GraphNodeData["tone"] {
  const relatedEdges = edges.filter((edge) => edge.source === nodeId || edge.target === nodeId);
  if (relatedEdges.some((edge) => edge.type === "MATCHES")) {
    return "positive";
  }
  if (relatedEdges.some((edge) => edge.type === "FAILED_CONDITION")) {
    return "negative";
  }
  return "neutral";
}

function spreadY(index: number, total: number, centerY: number, spacing: number) {
  return centerY + (index - (total - 1) / 2) * spacing;
}

function hasSessionAnswers(sessionGraph: SessionGraphResponse | null) {
  if (!sessionGraph) {
    return false;
  }
  return sessionGraph.nodes.some((node) => {
    const type = normalizeBackendType(node.type);
    if (type === "CONDITION") {
      return node.data.value !== undefined && node.data.value !== null && node.data.value !== "";
    }
    if (type === "POLICY") {
      return typeof node.data.eligibilityStatus === "string";
    }
    return false;
  });
}

function isApplicablePolicyNode(node: SessionGraphNode) {
  return normalizeBackendType(node.type) === "POLICY" && eligibleStatuses.has(eligibilityStatusValue(node));
}

function isIneligiblePolicyNode(node: SessionGraphNode | undefined) {
  return node !== undefined && normalizeBackendType(node.type) === "POLICY" && ineligibleStatuses.has(eligibilityStatusValue(node));
}

function getPolicyIdFromGraphNode(node: SessionGraphNode) {
  return typeof node.data.policyId === "string" ? node.data.policyId : node.id.replace(/^POLICY:/, "");
}

function policyGridPosition(index: number, total: number, answered = false): GraphPoint {
  const columns = answered ? (total > 10 ? 2 : 1) : total > 8 ? 3 : total > 4 ? 2 : 1;
  const column = index % columns;
  const row = Math.floor(index / columns);
  const rows = Math.ceil(total / columns);
  const x = columns === 1 ? 660 : columns === 2 ? 560 + column * 500 : 500 + column * 360;
  const y = spreadY(row, rows, 360, answered ? 220 : 190);
  return { x, y };
}

function sortPoliciesForGraph(
  policies: PolicySummaryResponse[],
  evaluationByPolicyId: Map<string, SessionGraphNode>,
) {
  return [...policies].sort((left, right) => {
    const leftEvaluation = evaluationByPolicyId.get(left.policyId);
    const rightEvaluation = evaluationByPolicyId.get(right.policyId);
    const leftEligible = leftEvaluation && isApplicablePolicyNode(leftEvaluation) ? 1 : 0;
    const rightEligible = rightEvaluation && isApplicablePolicyNode(rightEvaluation) ? 1 : 0;
    if (leftEligible !== rightEligible) {
      return rightEligible - leftEligible;
    }
    const leftIneligible = isIneligiblePolicyNode(leftEvaluation) ? 1 : 0;
    const rightIneligible = isIneligiblePolicyNode(rightEvaluation) ? 1 : 0;
    if (leftIneligible !== rightIneligible) {
      return leftIneligible - rightIneligible;
    }
    const leftScore = typeof leftEvaluation?.data.recommendationScore === "number" ? leftEvaluation.data.recommendationScore : 0;
    const rightScore = typeof rightEvaluation?.data.recommendationScore === "number" ? rightEvaluation.data.recommendationScore : 0;
    if (leftScore !== rightScore) {
      return rightScore - leftScore;
    }
    return left.title.localeCompare(right.title, "ko-KR");
  });
}

function conditionGridPosition(index: number, total: number): GraphPoint {
  return { x: 90, y: spreadY(index, total, 360, 132) };
}

function eligibilityStatusLabel(status: unknown) {
  if (status === "LIKELY_ELIGIBLE" || status === "eligible" || status === "ELIGIBLE") {
    return "신청 가능성 높음";
  }
  if (status === "NEEDS_CONFIRMATION") {
    return "추가 확인 필요";
  }
  if (status === "OFFICIAL_CONFIRMATION_REQUIRED") {
    return "공식 확인 필요";
  }
  if (status === "AVAILABLE_LATER") {
    return "추후 신청 가능";
  }
  if (status === "LIKELY_INELIGIBLE") {
    return "조건 불일치";
  }
  return "평가 전";
}

function policySummaryById(policySummaries: PolicySummaryResponse[]) {
  return new Map(policySummaries.map((policy) => [policy.policyId, policy]));
}

function createPolicyNodeFromSummary(policy: PolicySummaryResponse, index: number, total: number, answered = false): Node<GraphNodeData> {
  return {
    id: `POLICY:${policy.policyId}`,
    type: "policyNode",
    position: policyGridPosition(index, total, answered),
    data: {
      id: `POLICY:${policy.policyId}`,
      label: policy.title,
      description: `${policy.agency}\n${labelValue(policy.region)} / ${policy.applicationPeriod}`,
      icon: Landmark,
      status: "recommended",
      variant: "policy",
      tone: "neutral",
      backendType: "POLICY",
      backendData: {
        policyId: policy.policyId,
        categoryCode: policy.categoryCode,
        title: policy.title,
        agency: policy.agency,
        region: policy.region,
        applicationPeriod: policy.applicationPeriod,
        status: policy.status,
        officialSourceUrl: policy.officialSourceUrl,
      },
    },
  };
}

function enrichPolicyNode(node: Node<GraphNodeData>, summary: PolicySummaryResponse | undefined, index: number, total: number, answered = false): Node<GraphNodeData> {
  if (!summary) {
    return { ...node, position: policyGridPosition(index, total, answered) };
  }

  return {
    ...node,
    position: policyGridPosition(index, total, answered),
    data: {
      ...node.data,
      label: summary.title,
      description: `${summary.agency}\n${labelValue(summary.region)} / ${summary.applicationPeriod}`,
      backendData: {
        ...node.data.backendData,
        policyId: summary.policyId,
        categoryCode: summary.categoryCode,
        title: summary.title,
        agency: summary.agency,
        region: summary.region,
        applicationPeriod: summary.applicationPeriod,
        status: summary.status,
        officialSourceUrl: summary.officialSourceUrl,
      },
    },
  };
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
    return { x: 230, y: 360 };
  }
  if (type === "CATEGORY") {
    return { x: 430, y: 360 };
  }
  if (type === "POLICY") {
    return { x: 660, y: spreadY(index, total, 360, 220) };
  }
  if (type === "CONDITION") {
    return conditionGridPosition(index, total);
  }
  if (type === "ACTION") {
    return { x: 1160, y: spreadY(index, total, 360, 190) };
  }
  return { x: 660, y: spreadY(index, total, 540, 120) };
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

function createPolicyDetailNodes(policyNode: Node<GraphNodeData>, policyIndex: number): { nodes: Node<GraphNodeData>[]; edges: Edge[] } {
  const policyId = typeof policyNode.data.backendData?.policyId === "string" ? policyNode.data.backendData.policyId : policyNode.id;
  const region = labelValue(policyNode.data.backendData?.region);
  const supportType = labelValue(policyNode.data.backendData?.supportType);
  const applicationPeriod = labelValue(policyNode.data.backendData?.applicationPeriod);
  const details = [
    { id: "target", label: `지원 대상\n${region}`, value: region },
    { id: "support", label: `지원 내용\n${supportType}`, value: supportType },
    { id: "apply", label: `신청 기간\n${applicationPeriod}`, value: applicationPeriod },
  ];
  const detailX = policyNode.position.x + 330;

  return {
    nodes: details.map((detail, detailIndex) => ({
      id: `POLICY_DETAIL:${policyId}:${detail.id}`,
      type: "policyNode",
      position: {
        x: detailX,
        y: policyNode.position.y + (detailIndex - 1) * 64,
      },
      data: {
        id: `POLICY_DETAIL:${policyId}:${detail.id}`,
        label: detail.label,
        description: `${policyNode.data.label}의 ${detail.label.replace("\n", " 정보: ")}`,
        icon: ListChecks,
        status: policyNode.data.status,
        variant: "detail",
        tone: "positive",
        backendType: "POLICY_DETAIL",
        backendData: {
          ...policyNode.data.backendData,
          policyId,
          section: detail.id,
          value: detail.value,
        },
      },
    })),
    edges: details.map((detail, detailIndex) => ({
      id: `policy_detail:${policyId}:${detail.id}:${policyIndex}`,
      source: policyNode.id,
      target: `POLICY_DETAIL:${policyId}:${detail.id}`,
      sourceHandle: "right",
      targetHandle: "left",
      type: "straight",
      animated: false,
      style: {
        stroke: designTokens.color.graph.edge,
        strokeDasharray: detailIndex === 2 ? "6 5" : "3 5",
        strokeWidth: 1,
      },
    })),
  };
}

export function PolicyGraph({ selectedCategoryId, sessionGraph }: PolicyGraphProps) {
  const [selectedPolicy, setSelectedPolicy] = useState<GraphNodeData | null>(null);
  const [policySummaries, setPolicySummaries] = useState<PolicySummaryResponse[]>([]);
  const [policyDetails, setPolicyDetails] = useState<Record<string, PolicyDetailResponse>>({});
  const selectedCategory = categories.find(({ id }) => id === selectedCategoryId) ?? categories[0];

  useEffect(() => {
    const controller = new AbortController();
    listCategoryPolicies(selectedCategory.backendCategoryCode, controller.signal)
      .then((items) => setPolicySummaries(items))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setPolicySummaries([]);
      });
    return () => controller.abort();
  }, [selectedCategory.backendCategoryCode]);

  const handleGraphPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--policy-graph-spot-x", `${event.clientX - bounds.left}px`);
    event.currentTarget.style.setProperty("--policy-graph-spot-y", `${event.clientY - bounds.top}px`);
    event.currentTarget.style.setProperty("--policy-graph-spot-opacity", "1");
  };

  const handleGraphPointerLeave = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.style.setProperty("--policy-graph-spot-opacity", "0");
  };

  const { nodes, edges } = useMemo(() => {
    const answered = hasSessionAnswers(sessionGraph);
    const summariesById = policySummaryById(policySummaries);

    if (sessionGraph && sessionGraph.nodes.length > 0) {
      const totalByType = countNodesByType(sessionGraph.nodes);
      const indexByType = new Map<BackendNodeType | "UNKNOWN", number>();
      const sourceNodes = sessionGraph.nodes.filter((graphNode) => {
        const type = normalizeBackendType(graphNode.type);
        return type !== "POLICY" && type !== "ACTION";
      });
      const liveNodes: Node<GraphNodeData>[] = sourceNodes.map((graphNode) => {
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
            tone: type === "CONDITION" ? conditionToneForNode(graphNode.id, sessionGraph.edges) : "neutral",
          },
        };
      });
      const evaluationByPolicyId = new Map(
        sessionGraph.nodes
          .filter((graphNode) => normalizeBackendType(graphNode.type) === "POLICY")
          .map((graphNode) => [getPolicyIdFromGraphNode(graphNode), graphNode]),
      );
      const visiblePolicySummaries = sortPoliciesForGraph(policySummaries, evaluationByPolicyId);
      const visiblePolicyNodes = visiblePolicySummaries.map((summary, index) => {
        const graphNode = evaluationByPolicyId.get(summary.policyId);
        if (!graphNode) {
          return createPolicyNodeFromSummary(summary, index, visiblePolicySummaries.length, answered);
        }
        const baseNode: Node<GraphNodeData> = {
          id: graphNode.id,
          type: "policyNode",
          position: policyGridPosition(index, visiblePolicySummaries.length, answered),
          data: {
            id: graphNode.id,
            label: displayLabelForBackendNode(graphNode),
            description: descriptionForBackendNode(graphNode),
            icon: iconForBackendNode(graphNode),
            status: statusForBackendNode(graphNode),
            variant: "policy",
            backendType: graphNode.type,
            backendData: graphNode.data,
            tone: policyToneForBackendNode(graphNode),
          },
        };
        return enrichPolicyNode(baseNode, summariesById.get(summary.policyId), index, visiblePolicySummaries.length, answered);
      });
      const liveNodesWithoutPolicies = liveNodes.filter((node) => node.data.variant !== "policy");
      const composedNodes = [...liveNodesWithoutPolicies, ...visiblePolicyNodes];
      const visibleDetailGraph = visiblePolicyNodes
        .filter((node) => node.data.status === "eligible")
        .slice(0, answered ? 3 : 0)
        .map((node, index) => createPolicyDetailNodes(node, index));
      const detailNodes = visibleDetailGraph.flatMap((graph) => graph.nodes);
      const detailEdges = visibleDetailGraph.flatMap((graph) => graph.edges);
      const visibleNodes = [...composedNodes, ...detailNodes];
      const graphNodePositions = new Map<string, GraphPoint>(visibleNodes.map((node) => [node.id, node.position]));
      const visibleNodeIds = new Set(visibleNodes.map(({ id }) => id));
      const categoryNode = liveNodes.find((node) => node.data.variant === "category");
      const liveEdges: Edge[] = sessionGraph.edges
        .map((edge) => {
          if (edge.type === "HAS_FACT" && categoryNode) {
            return { ...edge, source: edge.target, target: categoryNode.id };
          }
          return edge;
        })
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
      const policyConnectionEdges: Edge[] =
        categoryNode && (!answered || liveEdges.every((edge) => !visiblePolicyNodes.some((node) => edge.target === node.id)))
          ? visiblePolicyNodes.map((node) => ({
              id: `category:${categoryNode.id}:${node.id}`,
              source: categoryNode.id,
              target: node.id,
              sourceHandle: "right",
              targetHandle: "left",
              type: "straight",
              animated: false,
              style: {
                stroke: designTokens.color.graph.edge,
                strokeWidth: answered ? 1.6 : 1.25,
              },
            }))
          : [];

      return { nodes: visibleNodes, edges: [...liveEdges, ...policyConnectionEdges, ...detailEdges] };
    }

    if (policySummaries.length > 0) {
      const center: Node<GraphNodeData> = {
        id: "couple",
        type: "policyNode",
        position: { x: 230, y: 330 },
        data: {
          id: "couple",
          label: "우리 부부",
          description: "질문에 답하면 신청 가능성이 높은 정책만 좁혀서 보여줍니다.",
          icon: UserRound,
          status: "recommended",
          variant: "central",
        },
      };
      const category: Node<GraphNodeData> = {
        id: `CATEGORY:${selectedCategory.backendCategoryCode}`,
        type: "policyNode",
        position: { x: 420, y: 330 },
        data: {
          id: `CATEGORY:${selectedCategory.backendCategoryCode}`,
          label: selectedCategory.label,
          description: `${selectedCategory.label} 주제에 등록된 정책 전체입니다.`,
          icon: selectedCategory.icon,
          status: "recommended",
          variant: "category",
          backendType: "CATEGORY",
          backendData: { categoryCode: selectedCategory.backendCategoryCode },
        },
      };
      const catalogNodes = policySummaries.map((policy, index) => createPolicyNodeFromSummary(policy, index, policySummaries.length));
      const categoryEdges: Edge[] = catalogNodes.map((node) => ({
        id: `category:${selectedCategory.backendCategoryCode}:${node.id}`,
        source: category.id,
        target: node.id,
        sourceHandle: "right",
        targetHandle: "left",
        type: "straight",
        animated: false,
        style: { stroke: designTokens.color.graph.edge, strokeWidth: 1.25 },
      }));

      return {
        nodes: [center, category, ...catalogNodes],
        edges: [
          {
            id: `couple:${category.id}`,
            source: center.id,
            target: category.id,
            sourceHandle: "right",
            targetHandle: "left",
            type: "straight",
            animated: false,
            style: { stroke: designTokens.color.graph.edge, strokeWidth: 1 },
          },
          ...categoryEdges,
        ],
      };
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
        icon: UsersRound,
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
  }, [policySummaries, selectedCategory, sessionGraph]);

  const selectedPolicyId = typeof selectedPolicy?.backendData?.policyId === "string" ? selectedPolicy.backendData.policyId : null;
  const selectedPolicyDetail = selectedPolicyId ? policyDetails[selectedPolicyId] : undefined;

  useEffect(() => {
    if (!selectedPolicyId || policyDetails[selectedPolicyId]) {
      return;
    }
    const controller = new AbortController();
    getPolicyDetail(selectedPolicyId, controller.signal)
      .then((detail) => setPolicyDetails((current) => ({ ...current, [selectedPolicyId]: detail })))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
      });
    return () => controller.abort();
  }, [policyDetails, selectedPolicyId]);

  return (
    <section className="relative flex h-full min-w-0 flex-col overflow-hidden rounded-3xl border border-brand-border bg-white shadow-card" aria-label="맞춤 정책 그래프">
      <header className="z-10 border-b border-brand-border bg-white/90 p-6 backdrop-blur">
        <h2 className="text-h3">맞춤 정책 그래프</h2>
        <p className="mt-1 text-body-sm text-text-secondary">
          {hasSessionAnswers(sessionGraph)
            ? `${selectedCategory.label} 답변 기준으로 신청 가능성이 확인된 정책을 표시합니다.`
            : `${selectedCategory.label} 주제의 등록 정책을 먼저 보여드립니다.`}
        </p>
      </header>

      <div
        className="policy-graph-bg relative h-full min-h-[560px] flex-1 overflow-hidden"
        onPointerMove={handleGraphPointerMove}
        onPointerLeave={handleGraphPointerLeave}
        style={{ "--policy-graph-spot-x": "50%", "--policy-graph-spot-y": "50%", "--policy-graph-spot-opacity": "0" } as CSSProperties}
      >
        <div className="policy-graph-bg__center-glow" aria-hidden="true" />
        <div className="policy-graph-bg__spotlight" aria-hidden="true" />
        <ReactFlow
          className="relative z-10"
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.3}
          maxZoom={1.8}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          edgesFocusable={false}
          nodesFocusable={false}
          panOnScroll
          panOnDrag
          zoomOnScroll
          zoomOnPinch
          preventScrolling={false}
          onNodeClick={(_, node) => {
            const data = node.data;
            if (data.variant !== "central") {
              setSelectedPolicy(data);
            }
          }}
        >
          <Controls position="top-right" showInteractive={false} />
          <Background color={designTokens.color.graph.backgroundLine} gap={32} size={1} />
        </ReactFlow>
      </div>

      {selectedPolicy && <PolicyModal policy={selectedPolicy} policyDetail={selectedPolicyDetail} onClose={() => setSelectedPolicy(null)} />}
    </section>
  );
}

function PolicyNode({ data }: NodeProps<Node<GraphNodeData>>) {
  const Icon = data.icon;
  const isCentral = data.variant === "central";
  const isPolicy = data.variant === "policy";
  const isCondition = data.variant === "condition";
  const isCategory = data.variant === "category";
  const isDetail = data.variant === "detail" || data.variant === "action";

  if (isPolicy) {
    const isEligible = data.status === "eligible";
    const isIneligible = data.tone === "negative";
    const policyBorderClass = isEligible
      ? "border-2 border-brand-primary"
      : isIneligible
        ? "border-2 border-[#C05A4B] bg-[#FFF7F5]"
        : "border border-brand-border opacity-85";
    const policyIconClass = isEligible
      ? "bg-brand-primary text-white"
      : isIneligible
        ? "bg-[#F7DEDA] text-[#C05A4B]"
        : "bg-brand-surface text-brand-primary";
    return (
      <div
        className={`relative flex min-h-[112px] w-[250px] cursor-pointer items-start gap-3 rounded-2xl bg-white px-4 py-4 text-left text-text-primary shadow-card transition hover:-translate-y-1 hover:bg-brand-surface-container ${
          policyBorderClass
        }`}
      >
        {handlePositions.map(({ id, position }) => (
          <Handle key={`target-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="target" position={position} />
        ))}
        {handlePositions.map(({ id, position }) => (
          <Handle key={`source-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="source" position={position} />
        ))}
        <div className={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${policyIconClass}`}>
          <Icon size={22} />
        </div>
        <div className="min-w-0">
          <span className="block whitespace-pre-line break-keep text-[13px] font-semibold leading-5">{data.label}</span>
          <span className="mt-2 block whitespace-pre-line text-[11px] font-medium leading-4 text-text-secondary">{data.description}</span>
        </div>
      </div>
    );
  }

  const conditionToneClass =
    data.tone === "positive"
      ? "border-2 border-brand-primary bg-white"
      : data.tone === "negative"
        ? "border-2 border-[#C05A4B] bg-[#FFF7F5]"
        : "border border-dashed border-brand-primary bg-white";
  const detailToneClass = data.tone === "positive" ? "border-brand-primary bg-white" : "border-brand-border bg-white";
  const iconToneClass = data.tone === "negative" ? "text-[#C05A4B]" : "text-brand-primary";

  return (
    <div
      className={`relative flex items-center justify-center text-center shadow-card ${
        isCentral
          ? "h-[136px] w-[136px] flex-col rounded-full border-2 border-brand-primary bg-white text-text-primary"
          : `cursor-pointer text-text-primary transition hover:-translate-y-1 hover:border-brand-primary hover:bg-brand-surface-container ${
              isCondition
                ? `h-[104px] w-[104px] flex-col rounded-full px-3 ${conditionToneClass}`
                : isCategory
                  ? "h-[112px] w-[112px] flex-col rounded-full border border-brand-border bg-brand-surface px-3"
                  : isDetail
                    ? `min-h-[48px] w-[168px] rounded-full border px-3 py-2 ${detailToneClass}`
                    : "h-[96px] w-[96px] flex-col rounded-full border border-brand-border bg-white px-3"
            }`
      }`}
    >
      {handlePositions.map(({ id, position }) => (
        <Handle key={`target-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="target" position={position} />
      ))}
      {handlePositions.map(({ id, position }) => (
        <Handle key={`source-${id}`} id={id} className="!h-0 !w-0 !border-0 !bg-transparent" type="source" position={position} />
      ))}
      <Icon size={isCentral ? 34 : isDetail ? 16 : 24} className={`${isDetail ? "mr-2 shrink-0" : "mb-2"} ${iconToneClass}`} />
      <span className={`${isCentral ? "text-body-sm font-semibold" : isDetail ? "whitespace-pre-line text-left text-[11px] font-medium leading-4" : "whitespace-pre-line text-[11px] font-medium leading-4"}`}>
        {data.label}
      </span>
    </div>
  );
}

const backendFieldLabels: Record<string, string> = {
  categoryCode: "주제",
  eligibilityStatus: "자격 상태",
  evaluationState: "평가 상태",
  factKey: "조건",
  value: "값",
  region: "지역",
  supportType: "지원 유형",
  section: "상세 항목",
  agency: "기관",
  applicationPeriod: "신청 기간",
  officialSourceUrl: "공식 URL",
};

const detailSectionLabels: Record<string, string> = {
  target: "지원 대상",
  support: "지원 내용",
  apply: "신청 기간",
};

function formatBackendValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "미확인";
  }
  return labelValue(value);
}

function visibleBackendEntries(data: Record<string, unknown> | undefined) {
  if (!data) {
    return [];
  }
  return Object.entries(data).filter(([key]) =>
    ["eligibilityStatus", "evaluationState", "factKey", "value", "categoryCode", "region", "supportType", "section", "agency", "applicationPeriod"].includes(key),
  );
}

function formatBackendEntryValue(key: string, value: unknown) {
  if (key === "eligibilityStatus") {
    return eligibilityStatusLabel(value);
  }
  if (key === "evaluationState") {
    return value === "ACTIVE" || value === "complete" ? "최신 답변 기준" : formatBackendValue(value);
  }
  if (key === "section") {
    return detailSectionLabels[String(value)] ?? formatBackendValue(value);
  }
  return formatBackendValue(value);
}

function PolicyModal({ policy, policyDetail, onClose }: { policy: GraphNodeData; policyDetail?: PolicyDetailResponse; onClose: () => void }) {
  const Icon = policy.icon;
  const backendEntries = visibleBackendEntries(policy.backendData);
  const sourceUrl =
    policyDetail?.source.url ??
    (typeof policy.backendData?.officialSourceUrl === "string" ? policy.backendData.officialSourceUrl : null);
  const sourceLabel = policyDetail?.source.label ?? "공식 페이지";
  const section = typeof policy.backendData?.section === "string" ? policy.backendData.section : null;
  const modalTitle = policyDetail?.title ?? (typeof policy.backendData?.title === "string" ? policy.backendData.title : policy.label);
  const modalDescription = policyDetail?.summary ?? policy.description;
  const eligibilityStatus = policy.backendData?.eligibilityStatus;

  return (
    <>
      <div className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-[4px] brightness-95" onClick={onClose} />
      <article className="fixed left-1/2 top-1/2 z-[101] flex max-h-[calc(100vh-48px)] w-[min(520px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 scale-100 flex-col overflow-hidden rounded-3xl bg-white opacity-100 shadow-card animate-modal-in">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-brand-border bg-brand-surface p-6">
          <div className="flex gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-primary text-white">
              <Icon size={24} />
            </div>
            <div>
              <p className="text-caption text-brand-primary">{section ? detailSectionLabels[section] ?? "정책 세부 정보" : "정책 상세"}</p>
              <h3 className="mt-1 whitespace-pre-line text-h3">{section ? policy.label : modalTitle}</h3>
            </div>
          </div>
          <button type="button" onClick={onClose} className="flex h-10 w-10 items-center justify-center rounded-xl text-text-secondary transition hover:bg-white">
            <X size={20} />
          </button>
        </header>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-6">
          <p className="text-body-md text-text-secondary">{modalDescription}</p>
          {policyDetail && (
            <dl className="grid grid-cols-1 gap-3 text-body-sm text-text-secondary sm:grid-cols-2">
              <div>
                <dt className="font-semibold text-text-primary">담당 기관</dt>
                <dd>{policyDetail.agency}</dd>
              </div>
              <div>
                <dt className="font-semibold text-text-primary">지역</dt>
                <dd>{labelValue(policyDetail.region)}</dd>
              </div>
              <div>
                <dt className="font-semibold text-text-primary">지원 유형</dt>
                <dd>{labelValue(policyDetail.supportType)}</dd>
              </div>
              <div>
                <dt className="font-semibold text-text-primary">신청 기간</dt>
                <dd>{policyDetail.applicationPeriod}</dd>
              </div>
            </dl>
          )}
          {eligibilityStatus !== null && eligibilityStatus !== undefined && (
            <div className="rounded-xl border border-brand-border bg-brand-surface p-4 text-body-sm text-text-secondary">
              <h4 className="text-h4 text-text-primary">추천 기준</h4>
              <p className="mt-2">
                {eligibilityStatusLabel(eligibilityStatus)}은 현재 입력한 조건에서 필수 조건 불일치가 없는 정책을 우선 보여주는 내부 정렬 결과입니다. 최종 자격과 모집 가능 여부는 공식 페이지에서
                다시 확인해야 합니다.
              </p>
            </div>
          )}
          <div className="rounded-xl border border-brand-border bg-white p-4">
            <h4 className="text-h4">{backendEntries.length > 0 ? "확인 데이터" : "확인된 조건"}</h4>
            <ul className="mt-3 space-y-2 text-body-sm text-text-secondary">
              {backendEntries.length > 0 ? (
                backendEntries.map(([key, value]) => (
                  <li key={key}>
                    {backendFieldLabels[key] ?? key}: {formatBackendEntryValue(key, value)}
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
          {sourceUrl ? (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand-primary text-body-md text-white transition duration-200 hover:brightness-90 active:scale-95"
            >
              <ExternalLink size={18} />
              {sourceLabel} 열기
            </a>
          ) : (
            <button type="button" disabled className="h-12 w-full rounded-xl bg-brand-surface text-body-md text-text-secondary">
              연결된 공식 URL이 없습니다
            </button>
          )}
        </div>
      </article>
    </>
  );
}
