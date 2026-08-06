import { RefreshCcw, Send, Sparkles } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import chatbotImage from "../assets/wedding-chatbot.svg";
import { categories, type PolicyCategory } from "../data/policies";
import { appConfig } from "../shared/config/appConfig";
import {
  createEvaluations,
  createSession,
  getNextQuestions,
  getSessionGraph,
  resetCategorySession,
  selectCategory,
  sendChatMessage,
  submitAnswer,
  type QuestionResponse,
  type SessionGraphResponse,
} from "../shared/api/chatbot";

type ChatMessage = {
  id: string;
  from: "bot" | "user";
  text: string;
  time: string;
};

const CHAT_STORAGE_KEY = "omgm.chatbot.conversations.v1";

const categoryMessages: Record<string, ChatMessage[]> = {
  housing: [
    { id: "housing-1", from: "bot", text: "Q1. 혼인신고를 완료했나요?", time: "10:01" },
    { id: "housing-2", from: "user", text: "예비부부예요.", time: "10:01" },
    { id: "housing-3", from: "bot", text: "Q2. 현재 서울에 거주하거나 전입 예정인가요?", time: "10:02" },
    { id: "housing-4", from: "user", text: "서울에 거주 중이에요.", time: "10:02" },
    { id: "housing-5", from: "bot", text: "Q3. 두 분 모두 무주택인가요?", time: "10:03" },
    { id: "housing-6", from: "user", text: "네, 무주택입니다.", time: "10:03" },
    { id: "housing-7", from: "bot", text: "좋아요. 우측 그래프에서 연결된 주거 정책을 눌러 상세 근거를 확인해보세요.", time: "10:04" },
  ],
  loan: [
    { id: "loan-1", from: "bot", text: "대출 지원을 확인할게요. Q1. 임대차 계약을 이미 진행했나요?", time: "10:01" },
    { id: "loan-2", from: "user", text: "계약 예정입니다.", time: "10:01" },
    { id: "loan-3", from: "bot", text: "Q2. 부부 합산 연소득 구간을 확인할 수 있나요?", time: "10:02" },
    { id: "loan-4", from: "user", text: "대략 7천만 원 이하예요.", time: "10:02" },
    { id: "loan-5", from: "bot", text: "전세자금, 임차보증금 이자지원 조건을 우선 연결해볼게요.", time: "10:03" },
  ],
  wedding: [
    { id: "wedding-1", from: "bot", text: "웨딩 지원을 확인할게요. Q1. 예식 예정일이 정해졌나요?", time: "10:01" },
    { id: "wedding-2", from: "user", text: "아직 후보 날짜만 있어요.", time: "10:01" },
    { id: "wedding-3", from: "bot", text: "Q2. 서울시 공공 예식장 이용을 고려하고 있나요?", time: "10:02" },
    { id: "wedding-4", from: "user", text: "네, 비용을 줄이고 싶어요.", time: "10:02" },
    { id: "wedding-5", from: "bot", text: "공공 예식장 예약 일정과 필요 서류 중심으로 안내할게요.", time: "10:03" },
  ],
  tax: [
    { id: "tax-1", from: "bot", text: "세제 혜택을 확인할게요. Q1. 혼인신고 예정 월이 있나요?", time: "10:01" },
    { id: "tax-2", from: "user", text: "올해 하반기로 생각 중이에요.", time: "10:01" },
    { id: "tax-3", from: "bot", text: "Q2. 세대 분리 또는 합가 계획이 있나요?", time: "10:02" },
    { id: "tax-4", from: "user", text: "합가할 예정입니다.", time: "10:02" },
    { id: "tax-5", from: "bot", text: "공제, 감면, 신고 일정에 영향을 주는 항목을 먼저 정리해드릴게요.", time: "10:03" },
  ],
  childcare: [
    { id: "childcare-1", from: "bot", text: "출산/육아 지원을 확인할게요. Q1. 출산 예정 또는 자녀 계획이 있나요?", time: "10:01" },
    { id: "childcare-2", from: "user", text: "내년에 계획하고 있어요.", time: "10:01" },
    { id: "childcare-3", from: "bot", text: "Q2. 신혼부부 주거 지원과 함께 확인할까요?", time: "10:02" },
    { id: "childcare-4", from: "user", text: "네, 같이 보고 싶어요.", time: "10:02" },
    { id: "childcare-5", from: "bot", text: "출산가구 주거 지원과 보육 지원을 연결해서 보여드릴게요.", time: "10:03" },
  ],
};

type ChatAreaProps = {
  selectedCategoryId: string;
  sessionGraph: SessionGraphResponse | null;
  onCategoryChange: (categoryId: string) => void;
  onGraphChange: (graph: SessionGraphResponse | null) => void;
};

function messageTime() {
  return new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
}

const questionLabels: Record<string, string> = {
  q_housing_region: "현재 거주 지역은 어디인가요?",
  q_housing_marital_status: "현재 혼인 상태는 어떻게 되나요?",
  q_housing_income: "부부 합산 연소득 구간은 어떻게 되나요?",
  q_housing_ownership: "현재 주택을 소유하고 있나요?",
  q_housing_lease_type: "고려 중인 주거 계약 유형은 무엇인가요?",
  q_cash_region: "현재 거주 지역은 어디인가요?",
  q_cash_marital_status: "현재 혼인 상태는 어떻게 되나요?",
  q_cash_marriage_registered: "혼인신고를 완료했나요?",
  q_cash_registration_date: "혼인신고일은 언제인가요?",
  q_childcare_region: "현재 거주 지역은 어디인가요?",
  q_childcare_pregnancy: "임신을 준비 중이거나 임신 중인가요?",
  q_childcare_has_child: "자녀가 있나요?",
  q_childcare_child_age: "가장 어린 자녀는 몇 개월인가요?",
  q_loan_region: "현재 거주 지역은 어디인가요?",
  q_loan_marital_status: "현재 혼인 상태는 어떻게 되나요?",
  q_loan_income: "부부 합산 연소득 구간은 어떻게 되나요?",
  q_loan_credit_need: "필요한 대출 지원 목적은 무엇인가요?",
  q_education_region: "현재 거주 지역은 어디인가요?",
  q_education_topic: "어떤 상담 주제가 필요한가요?",
  q_education_marital_status: "현재 혼인 상태는 어떻게 되나요?",
};

const optionLabels: Record<string, string> = {
  Seoul: "서울",
  Gyeonggi: "경기",
  Incheon: "인천",
  Busan: "부산",
  National: "전국",
  Daejeon: "대전",
  Jeonbuk: "전북",
  Sejong: "세종",
  engaged: "예비부부",
  newlywed: "신혼부부",
  married: "기혼",
  single: "미혼",
  unknown: "모름",
  under_50m: "5천만 원 미만",
  "50m_to_80m": "5천만-8천만 원",
  "80m_to_120m": "8천만-1억2천만 원",
  over_120m: "1억2천만 원 초과",
  no_home: "무주택",
  own_home: "주택 소유",
  jeonse: "전세",
  monthly_rent: "월세",
  purchase: "매매",
  true: "예",
  false: "아니오",
  preparing: "임신 준비",
  pregnant: "임신 중",
  not_applicable: "해당 없음",
  housing: "주거",
  wedding: "웨딩",
  settlement: "정착",
  housing_contract: "주거 계약",
  financial_counseling: "재무 상담",
  family_budget: "가계 예산",
};

const questionExamples: Record<string, string[]> = {
  q_housing_region: ["서울", "경기", "전국"],
  q_housing_marital_status: ["예비부부", "신혼부부", "기혼"],
  q_housing_income: ["5천만 원 미만", "5천만-8천만 원", "모름"],
  q_housing_ownership: ["무주택", "주택 소유", "모름"],
  q_housing_lease_type: ["전세", "월세", "매매"],
  q_cash_region: ["서울", "대전", "전국"],
  q_cash_marital_status: ["예비부부", "신혼부부", "기혼"],
  q_cash_marriage_registered: ["예", "아니오"],
  q_cash_registration_date: ["2026-05-24", "2026.05.24"],
  q_childcare_region: ["전국", "세종", "서울"],
  q_childcare_pregnancy: ["임신 준비", "임신 중", "해당 없음"],
  q_childcare_has_child: ["예", "아니오"],
  q_childcare_child_age: ["6", "12개월"],
  q_loan_region: ["전국", "서울", "경기"],
  q_loan_marital_status: ["예비부부", "신혼부부", "기혼"],
  q_loan_income: ["5천만 원 미만", "5천만-8천만 원", "모름"],
  q_loan_credit_need: ["주거", "웨딩", "정착"],
  q_education_region: ["전국", "서울", "경기"],
  q_education_topic: ["주거 계약", "재무 상담", "가계 예산"],
  q_education_marital_status: ["예비부부", "신혼부부", "기혼"],
};

function formatQuestionGuide(question: QuestionResponse) {
  const examples =
    questionExamples[question.questionId] ??
    (question.options.length > 0 ? question.options.slice(0, 3).map(({ value }) => optionLabels[value] ?? value) : []);

  if (question.answerType === "date") {
    return "입력 예시: 2026-05-24 또는 2026.05.24";
  }

  if (question.answerType === "number") {
    return "입력 예시: 6 또는 12개월";
  }

  if (examples.length > 0) {
    return `입력 예시: ${examples.join(", ")}`;
  }

  return "질문에 맞는 값을 짧게 입력해 주세요.";
}

function formatQuestion(question: QuestionResponse) {
  const prompt = questionLabels[question.questionId] ?? question.prompt;
  const options = question.options.map(({ value }) => optionLabels[value] ?? value);

  if (options.length === 0) {
    return `${prompt}\n${formatQuestionGuide(question)}`;
  }

  return `${prompt}\n선택지: ${options.join(", ")}\n${formatQuestionGuide(question)}`;
}

function normalizeAnswer(input: string, question: QuestionResponse): string | number | boolean | null {
  const text = input.trim().toLowerCase();
  const optionValues = question.options.map(({ value }) => value);

  for (const option of question.options) {
    const display = optionLabels[option.value] ?? option.label;
    if (text === option.value.toLowerCase() || text === option.label.toLowerCase() || text === display.toLowerCase()) {
      return question.answerType === "boolean" ? option.value === "true" : option.value;
    }
  }

  const aliases: Record<string, string> = {
    서울: "Seoul",
    seoul: "Seoul",
    경기: "Gyeonggi",
    경기도: "Gyeonggi",
    gyeonggi: "Gyeonggi",
    인천: "Incheon",
    부산: "Busan",
    전국: "National",
    national: "National",
    대전: "Daejeon",
    전북: "Jeonbuk",
    세종: "Sejong",
    예비부부: "engaged",
    예비: "engaged",
    engaged: "engaged",
    신혼부부: "newlywed",
    신혼: "newlywed",
    newlywed: "newlywed",
    기혼: "married",
    married: "married",
    미혼: "single",
    single: "single",
    모름: "unknown",
    몰라요: "unknown",
    unknown: "unknown",
    무주택: "no_home",
    "주택 없음": "no_home",
    유주택: "own_home",
    "주택 소유": "own_home",
    전세: "jeonse",
    월세: "monthly_rent",
    매매: "purchase",
    준비: "preparing",
    "임신 준비": "preparing",
    임신중: "pregnant",
    "임신 중": "pregnant",
    "해당 없음": "not_applicable",
    주거: "housing",
    웨딩: "wedding",
    정착: "settlement",
    "주거 계약": "housing_contract",
    "재무 상담": "financial_counseling",
    "가계 예산": "family_budget",
  };

  if (question.answerType === "boolean") {
    if (["예", "네", "yes", "y", "true", "완료", "있어요", "있음"].includes(text)) {
      return true;
    }
    if (["아니오", "아니요", "no", "n", "false", "미완료", "없어요", "없음"].includes(text)) {
      return false;
    }
  }

  if (question.answerType === "number") {
    const number = Number(input.replace(/[^0-9.-]/g, ""));
    return Number.isFinite(number) ? number : null;
  }

  if (question.answerType === "date") {
    const match = input.trim().match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$/);
    if (!match) {
      return null;
    }
    const [, year, month, day] = match;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  for (const [alias, value] of Object.entries(aliases)) {
    if (text.includes(alias) && optionValues.includes(value)) {
      return value;
    }
  }

  if (optionValues.includes("under_50m") && /(5천|5000|50m|이하|미만)/.test(text)) {
    return "under_50m";
  }
  if (optionValues.includes("50m_to_80m") && /(7천|7000|80m|8천)/.test(text)) {
    return "50m_to_80m";
  }
  if (optionValues.includes("80m_to_120m") && /(1억|120m|1억2천)/.test(text)) {
    return "80m_to_120m";
  }

  return null;
}

function fallbackMessages(category: PolicyCategory) {
  return categoryMessages[category.id] ?? categoryMessages.housing;
}

function readStoredMessages(): Record<string, ChatMessage[]> {
  try {
    const raw = window.localStorage?.getItem(CHAT_STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    return Object.fromEntries(
      Object.entries(parsed as Record<string, ChatMessage[]>).map(([categoryId, messages]) => [
        categoryId,
        messages.filter((message) => !/^(주거|대출|웨딩|세제 혜택|출산\/육아).*(실제 질문 엔진|질문 흐름)/.test(message.text)),
      ]),
    );
  } catch {
    return {};
  }
}

function writeStoredMessages(messagesByCategory: Record<string, ChatMessage[]>) {
  try {
    window.localStorage?.setItem(CHAT_STORAGE_KEY, JSON.stringify(messagesByCategory));
  } catch {
    return;
  }
}

export function ChatArea({ selectedCategoryId, sessionGraph, onCategoryChange, onGraphChange }: ChatAreaProps) {
  const selectedCategory = categories.find(({ id }) => id === selectedCategoryId) ?? categories[0];
  const isLiveMode = appConfig.apiMode === "live";
  const initialStoredMessages = useRef(readStoredMessages());
  const messageId = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const loadedCategoryIds = useRef(new Set<string>());
  const [messagesByCategory, setMessagesByCategory] = useState<Record<string, ChatMessage[]>>(() => initialStoredMessages.current);
  const [draft, setDraft] = useState("");
  const [activeQuestionsByCategory, setActiveQuestionsByCategory] = useState<Record<string, QuestionResponse | null>>({});
  const [loading, setLoading] = useState(false);
  const [liveIssuesByCategory, setLiveIssuesByCategory] = useState<Record<string, string | null>>({});
  const [sessionResetNonce, setSessionResetNonce] = useState(0);
  const messages = messagesByCategory[selectedCategory.id] ?? (isLiveMode ? [] : fallbackMessages(selectedCategory));
  const activeQuestion = activeQuestionsByCategory[selectedCategory.id] ?? null;
  const liveIssue = liveIssuesByCategory[selectedCategory.id] ?? null;
  const appendMessage = useCallback((categoryId: string, from: ChatMessage["from"], text: string) => {
    setMessagesByCategory((current) => ({
      ...current,
      [categoryId]: [
        ...(current[categoryId] ?? []),
        {
          id: `live-${Date.now()}-${messageId.current++}`,
          from,
          text,
          time: messageTime(),
        },
      ],
    }));
  }, []);

  useEffect(() => {
    writeStoredMessages(messagesByCategory);
  }, [messagesByCategory]);

  useEffect(() => {
    const controller = new AbortController();
    const categoryId = selectedCategory.id;

    async function loadLiveCategory() {
      setLoading(true);
      setLiveIssuesByCategory((current) => ({ ...current, [categoryId]: null }));
      onGraphChange(null);

      try {
        await createSession(controller.signal);
        await selectCategory(selectedCategory.backendCategoryCode, controller.signal);
        const [questions, graph] = await Promise.all([getNextQuestions(controller.signal), getSessionGraph(selectedCategory.backendCategoryCode, controller.signal)]);
        onGraphChange(graph);
        const nextQuestion = questions.items[0] ?? null;
        setActiveQuestionsByCategory((current) => ({ ...current, [categoryId]: nextQuestion }));
        setMessagesByCategory((current) => {
          if ((current[categoryId]?.length ?? 0) > 0 && loadedCategoryIds.current.has(categoryId)) {
            return current;
          }
          return {
            ...current,
            [categoryId]: current[categoryId] ?? [
              {
                id: `live-intro-${categoryId}`,
                from: "bot",
                text: nextQuestion ? formatQuestion(nextQuestion) : "현재 추가 질문이 없습니다. 궁금한 내용을 입력하면 연결된 정책 기준으로 답변해드릴게요.",
                time: messageTime(),
              },
            ],
          };
        });
        loadedCategoryIds.current.add(categoryId);
      } catch {
        setLiveIssuesByCategory((current) => ({ ...current, [categoryId]: "백엔드 세션 API에 연결하지 못해 목업 대화로 표시 중입니다." }));
        setMessagesByCategory((current) => ({
          ...current,
          [categoryId]: current[categoryId] ?? fallbackMessages(selectedCategory),
        }));
      } finally {
        setLoading(false);
      }
    }

    if (isLiveMode) {
      void loadLiveCategory();
      return () => controller.abort();
    }

    setMessagesByCategory((current) => ({
      ...current,
      [categoryId]: current[categoryId] ?? fallbackMessages(selectedCategory),
    }));
    setActiveQuestionsByCategory((current) => ({ ...current, [categoryId]: null }));
    setLiveIssuesByCategory((current) => ({ ...current, [categoryId]: null }));
    return () => controller.abort();
  }, [isLiveMode, onGraphChange, selectedCategory, sessionResetNonce]);

  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages.length, selectedCategoryId, loading]);

  const optionHint = useMemo(() => {
    if (!activeQuestion) {
      return null;
    }

    return formatQuestionGuide(activeQuestion);
  }, [activeQuestion]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const answerText = draft.trim();

    if (!answerText || loading) {
      return;
    }

    setDraft("");
    appendMessage(selectedCategory.id, "user", answerText);

    if (!isLiveMode) {
      appendMessage(selectedCategory.id, "bot", "현재 실제 답변을 준비할 수 없습니다. 잠시 후 다시 시도해 주세요.");
      return;
    }

    if (!activeQuestion) {
      setLoading(true);
      try {
        const response = await sendChatMessage(answerText);
        appendMessage(selectedCategory.id, "bot", response.answer || "연결된 정책 기준으로 답변할 내용을 찾지 못했습니다.");
      } catch {
        appendMessage(selectedCategory.id, "bot", "추가 질문 답변 중 문제가 발생했습니다. 백엔드 실행 상태를 확인해 주세요.");
      } finally {
        setLoading(false);
      }
      return;
    }

    const value = normalizeAnswer(answerText, activeQuestion);
    if (value === null) {
      appendMessage(selectedCategory.id, "bot", optionHint ? `입력 형식이 맞지 않습니다.\n${optionHint}` : "입력 형식이 맞지 않습니다. 질문에 맞는 값을 짧게 입력해 주세요.");
      return;
    }

    setLoading(true);
    try {
      const result = await submitAnswer(activeQuestion, value);
      if (result.conflicts.length > 0) {
        const conflictQuestion = result.conflicts[0]?.question;
        setActiveQuestionsByCategory((current) => ({ ...current, [selectedCategory.id]: conflictQuestion ?? activeQuestion }));
        appendMessage(selectedCategory.id, "bot", conflictQuestion ? `이전 답변과 충돌합니다.\n${formatQuestion(conflictQuestion)}` : "이전 답변과 충돌합니다. 기존 조건을 먼저 확인해 주세요.");
        return;
      }

      const nextQuestion = result.nextQuestions[0] ?? null;
      setActiveQuestionsByCategory((current) => ({ ...current, [selectedCategory.id]: nextQuestion }));
      if (nextQuestion) {
        appendMessage(selectedCategory.id, "bot", formatQuestion(nextQuestion));
        return;
      }

      await createEvaluations();
      const graph = await getSessionGraph(selectedCategory.backendCategoryCode);
      onGraphChange(graph);
      appendMessage(selectedCategory.id, "bot", "답변을 저장했고 정책 그래프를 갱신했어요. 우측 그래프에서 연결된 정책과 근거를 확인해보세요.");
    } catch {
      appendMessage(selectedCategory.id, "bot", "답변 저장 중 문제가 발생했습니다. 백엔드 실행 상태와 세션 설정을 확인해 주세요.");
    } finally {
      setLoading(false);
    }
  }

  async function handleNewSession() {
    const categoryId = selectedCategory.id;
    setLoading(true);
    try {
      if (isLiveMode) {
        await resetCategorySession(selectedCategory.backendCategoryCode);
      }
    } catch {
      // 카테고리 초기화 API가 실패해도 현재 화면은 새 주제 대화로 다시 시작한다.
    } finally {
      loadedCategoryIds.current.delete(categoryId);
      setMessagesByCategory((current) => {
        const next = { ...current };
        delete next[categoryId];
        return next;
      });
      setActiveQuestionsByCategory((current) => ({ ...current, [categoryId]: null }));
      setLiveIssuesByCategory((current) => ({ ...current, [categoryId]: null }));
      setDraft("");
      onGraphChange(null);
      setSessionResetNonce((value) => value + 1);
      setLoading(false);
    }
  }

  return (
    <section id="chat" className="flex h-full min-w-0 flex-col overflow-hidden rounded-3xl border border-brand-border bg-white shadow-card" aria-label="챗봇 대화 영역">
      <header className="border-b border-brand-border p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-h3">정책 챗봇</h2>
            <p className="mt-1 text-body-sm text-text-secondary">주제를 선택하면 꼭 필요한 질문만 드려요.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                void handleNewSession();
              }}
              className="flex h-10 items-center gap-2 rounded-lg border border-brand-border bg-white px-3 text-caption text-text-secondary transition hover:border-brand-primary hover:text-brand-primary"
            >
              <RefreshCcw size={15} />
              새 세션
            </button>
            <div className="hidden h-12 w-12 items-center justify-center rounded-xl bg-brand-surface text-brand-primary sm:flex">
              <Sparkles size={22} />
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-center overflow-x-auto px-1 pb-3 pt-2">
          <div className="flex min-w-max gap-3">
            {categories.map(({ id, label, icon: Icon }) => {
              const selected = selectedCategoryId === id;
              return (
                <button
                  type="button"
                  key={id}
                  onClick={() => onCategoryChange(id)}
                  className={`flex h-[110px] w-[90px] shrink-0 flex-col items-center justify-center gap-3 rounded-arch px-2 transition duration-200 hover:-translate-y-1 hover:bg-brand-primary-hover hover:text-white ${
                    selected ? "border-b-4 border-text-primary bg-brand-primary-strong text-white shadow-floating" : "bg-brand-surface text-text-secondary"
                  }`}
                >
                  <Icon size={24} />
                  <span className="text-center text-caption">{label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto bg-brand-surface/35 p-6">
        {liveIssue && <p className="rounded-xl border border-brand-border bg-white p-3 text-caption text-text-secondary">{liveIssue}</p>}
        {isLiveMode && sessionGraph?.truncated && <p className="rounded-xl border border-brand-border bg-white p-3 text-caption text-text-secondary">그래프 노드가 많아 일부만 표시됩니다.</p>}
        {messages.map((message) => {
          const isUser = message.from === "user";
          return (
            <div key={message.id} className={`flex items-start gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
              {!isUser && <img src={chatbotImage} alt="" className="h-8 w-8 rounded-full border border-brand-border bg-white object-cover" />}
              <div className={`max-w-[70%] ${isUser ? "text-right" : ""}`}>
                <div
                  className={`rounded-xl p-4 text-body-sm shadow-sm ${
                    isUser ? "bg-brand-primary text-white" : "border border-brand-border bg-white text-text-primary"
                  }`}
                >
                  {message.text.split("\n").map((line) => (
                    <span key={line} className="block">
                      {line}
                    </span>
                  ))}
                </div>
                <time className="mt-1 block text-caption text-text-secondary">{message.time}</time>
              </div>
              {isUser && <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-surface-container text-caption text-brand-primary">나</div>}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <form
        className="border-t border-brand-border bg-white p-5"
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
      >
        <div className="relative">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            className="h-14 w-full rounded-xl border border-brand-border bg-white pl-5 pr-14 text-body-md text-text-primary outline-none transition focus:border-brand-primary focus:ring-4 focus:ring-brand-surface"
            placeholder={loading ? "백엔드와 통신 중입니다..." : activeQuestion ? formatQuestionGuide(activeQuestion).replace("입력 예시: ", "예: ") : `${selectedCategory.label} 정책 조건을 입력하세요...`}
            disabled={loading}
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl bg-brand-primary text-white transition hover:brightness-90 active:scale-95"
            aria-label="질문 보내기"
          >
            <Send size={18} />
          </button>
        </div>
      </form>
    </section>
  );
}
