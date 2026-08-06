import { deleteJson, getJson, postJson } from "./client";

export type QuestionOption = {
  label: string;
  value: string;
};

export type QuestionResponse = {
  questionId: string;
  factKey: string;
  prompt: string;
  answerType: string;
  required: boolean;
  priority: number;
  parentQuestionId: string | null;
  showCondition: { factKey: string; equals: unknown } | null;
  options: QuestionOption[];
  isConflictResolution: boolean;
  conflictReason: string | null;
};

export type NextQuestionsResponse = {
  categoryCode: string | null;
  items: QuestionResponse[];
  complete: boolean;
};

export type SubmitAnswersResponse = {
  status: string;
  stored: string[];
  conflicts: Array<{
    factKey: string;
    existingValue: unknown;
    submittedValue: unknown;
    question: QuestionResponse | null;
  }>;
  nextQuestions: QuestionResponse[];
};

export type PolicyEvaluationResponse = {
  policyId: string;
  eligibilityStatus: string;
  evaluationState: string;
  recommendationScore: number;
  evidence: {
    satisfied: Array<Record<string, unknown>>;
    unsatisfied: Array<Record<string, unknown>>;
    needsConfirmation: Array<Record<string, unknown>>;
    officialConfirmationRequired: Array<Record<string, unknown>>;
  };
  evaluatedAt: string;
  updatedAt: string;
};

export type CreateEvaluationsResponse = {
  status: string;
  items: PolicyEvaluationResponse[];
};

export type SessionGraphNode = {
  id: string;
  type: string;
  label: string;
  data: Record<string, unknown>;
};

export type SessionGraphEdge = {
  id: string;
  type: string;
  source: string;
  target: string;
  data: Record<string, unknown>;
};

export type SessionGraphResponse = {
  nodes: SessionGraphNode[];
  edges: SessionGraphEdge[];
  nodeCount: number;
  edgeCount: number;
  truncated: boolean;
};

export type AIExplanationResponse = {
  policyId: string | null;
  eligibilityStatus: string;
  evaluationState: string | null;
  aiStatus: string;
  answer: string;
  citations: Array<{
    sourceId: string;
    policyId: string;
    title: string;
    url: string;
    sourceLabel: string;
    evidenceId: string;
    excerpt: string | null;
    sourceLocation: string | null;
    similarity: number | null;
  }>;
};

export type PolicySummaryResponse = {
  policyId: string;
  categoryCode: string;
  title: string;
  agency: string;
  region: string;
  applicationPeriod: string;
  status: string;
  officialSourceUrl: string;
  reviewedAt: string;
};

export type PolicyDetailResponse = {
  policyId: string;
  categoryCode: string;
  title: string;
  agency: string;
  region: string;
  summary: string;
  applicationPeriod: string;
  supportType: string;
  status: string;
  source: {
    label: string;
    url: string;
    reviewedAt: string;
  };
};

export function createSession(signal?: AbortSignal) {
  return postJson<{ status: string }>("/api/v1/session", undefined, { signal });
}

export function deleteSession(signal?: AbortSignal) {
  return deleteJson("/api/v1/session", { signal });
}

export function selectCategory(categoryCode: string, signal?: AbortSignal) {
  return postJson<{ categoryCode: string; status: string }>("/api/v1/session/category", { categoryCode }, { signal });
}

export function getNextQuestions(signal?: AbortSignal) {
  return getJson<NextQuestionsResponse>("/api/v1/session/questions/next", { signal });
}

export function submitAnswer(question: QuestionResponse, value: unknown, signal?: AbortSignal) {
  return postJson<SubmitAnswersResponse>(
    "/api/v1/session/answers",
    {
      answers: [
        {
          questionId: question.questionId,
          factKey: question.factKey,
          value,
          confirmed: true,
        },
      ],
    },
    { signal },
  );
}

export function createEvaluations(signal?: AbortSignal) {
  return postJson<CreateEvaluationsResponse>("/api/v1/session/evaluations", undefined, { signal });
}

export function getSessionGraph(categoryCode: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ category: categoryCode, max_nodes: "18" });
  return getJson<SessionGraphResponse>(`/api/v1/session/graph?${params.toString()}`, { signal });
}

export function sendChatMessage(message: string, signal?: AbortSignal) {
  return postJson<AIExplanationResponse>("/api/chat", { message }, { signal });
}

export function listCategoryPolicies(categoryCode: string, signal?: AbortSignal) {
  return getJson<PolicySummaryResponse[]>(`/api/categories/${categoryCode}/policies`, { signal });
}

export function getPolicyDetail(policyId: string, signal?: AbortSignal) {
  return getJson<PolicyDetailResponse>(`/api/policies/${policyId}`, { signal });
}
