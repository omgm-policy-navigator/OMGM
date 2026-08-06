import { Send, Sparkles } from "lucide-react";
import { useState } from "react";
import chatbotImage from "../assets/wedding-chatbot.svg";
import { categories } from "../data/policies";

type ChatMessage = {
  id: number;
  from: "bot" | "user";
  text: string;
  time: string;
};

const categoryMessages: Record<string, ChatMessage[]> = {
  housing: [
    { id: 1, from: "bot", text: "Q1. 혼인신고를 완료했나요?", time: "10:01" },
    { id: 2, from: "user", text: "예비부부예요.", time: "10:01" },
    { id: 3, from: "bot", text: "Q2. 현재 서울에 거주하거나 전입 예정인가요?", time: "10:02" },
    { id: 4, from: "user", text: "서울에 거주 중이에요.", time: "10:02" },
    { id: 5, from: "bot", text: "Q3. 두 분 모두 무주택인가요?", time: "10:03" },
    { id: 6, from: "user", text: "네, 무주택입니다.", time: "10:03" },
    { id: 7, from: "bot", text: "좋아요. 우측 그래프에서 연결된 주거 정책을 눌러 상세 근거를 확인해보세요.", time: "10:04" },
  ],
  loan: [
    { id: 1, from: "bot", text: "대출 지원을 확인할게요. Q1. 임대차 계약을 이미 진행했나요?", time: "10:01" },
    { id: 2, from: "user", text: "계약 예정입니다.", time: "10:01" },
    { id: 3, from: "bot", text: "Q2. 부부 합산 연소득 구간을 확인할 수 있나요?", time: "10:02" },
    { id: 4, from: "user", text: "대략 7천만 원 이하예요.", time: "10:02" },
    { id: 5, from: "bot", text: "전세자금, 임차보증금 이자지원 조건을 우선 연결해볼게요.", time: "10:03" },
  ],
  wedding: [
    { id: 1, from: "bot", text: "웨딩 지원을 확인할게요. Q1. 예식 예정일이 정해졌나요?", time: "10:01" },
    { id: 2, from: "user", text: "아직 후보 날짜만 있어요.", time: "10:01" },
    { id: 3, from: "bot", text: "Q2. 서울시 공공 예식장 이용을 고려하고 있나요?", time: "10:02" },
    { id: 4, from: "user", text: "네, 비용을 줄이고 싶어요.", time: "10:02" },
    { id: 5, from: "bot", text: "공공 예식장 예약 일정과 필요 서류 중심으로 안내할게요.", time: "10:03" },
  ],
  tax: [
    { id: 1, from: "bot", text: "세제 혜택을 확인할게요. Q1. 혼인신고 예정 월이 있나요?", time: "10:01" },
    { id: 2, from: "user", text: "올해 하반기로 생각 중이에요.", time: "10:01" },
    { id: 3, from: "bot", text: "Q2. 세대 분리 또는 합가 계획이 있나요?", time: "10:02" },
    { id: 4, from: "user", text: "합가할 예정입니다.", time: "10:02" },
    { id: 5, from: "bot", text: "공제, 감면, 신고 일정에 영향을 주는 항목을 먼저 정리해드릴게요.", time: "10:03" },
  ],
  childcare: [
    { id: 1, from: "bot", text: "출산/육아 지원을 확인할게요. Q1. 출산 예정 또는 자녀 계획이 있나요?", time: "10:01" },
    { id: 2, from: "user", text: "내년에 계획하고 있어요.", time: "10:01" },
    { id: 3, from: "bot", text: "Q2. 신혼부부 주거 지원과 함께 확인할까요?", time: "10:02" },
    { id: 4, from: "user", text: "네, 같이 보고 싶어요.", time: "10:02" },
    { id: 5, from: "bot", text: "출산가구 주거 지원과 보육 지원을 연결해서 보여드릴게요.", time: "10:03" },
  ],
};

export function ChatArea() {
  const [selectedCategoryId, setSelectedCategoryId] = useState(categories[0]?.id);
  const selectedCategory = categories.find(({ id }) => id === selectedCategoryId) ?? categories[0];
  const messages = categoryMessages[selectedCategory.id] ?? categoryMessages.housing;

  return (
    <section id="chat" className="flex h-full min-w-0 flex-col overflow-hidden rounded-3xl border border-brand-border bg-white shadow-card" aria-label="챗봇 대화 영역">
      <header className="border-b border-brand-border p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-h3">정책 챗봇</h2>
            <p className="mt-1 text-body-sm text-text-secondary">주제를 선택하면 꼭 필요한 질문만 드려요.</p>
          </div>
          <div className="hidden h-12 w-12 items-center justify-center rounded-xl bg-brand-surface text-brand-primary sm:flex">
            <Sparkles size={22} />
          </div>
        </div>

        <div className="mt-6 flex justify-center overflow-x-auto pb-2">
          <div className="flex min-w-max gap-3">
            {categories.map(({ id, label, icon: Icon }) => {
              const selected = selectedCategoryId === id;
              return (
                <button
                  type="button"
                  key={id}
                  onClick={() => setSelectedCategoryId(id)}
                  className={`flex h-[110px] w-[90px] shrink-0 flex-col items-center justify-center gap-3 rounded-arch px-2 transition duration-200 hover:-translate-y-1 hover:bg-[#5F966D] hover:text-white ${
                    selected ? "border-b-4 border-text-primary bg-[#4F8F60] text-white shadow-floating" : "bg-brand-surface text-text-secondary"
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
                  {message.text}
                </div>
                <time className="mt-1 block text-caption text-text-secondary">{message.time}</time>
              </div>
              {isUser && <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-surface-container text-caption text-brand-primary">나</div>}
            </div>
          );
        })}
      </div>

      <form className="border-t border-brand-border bg-white p-5">
        <div className="relative">
          <input
            className="h-14 w-full rounded-xl border border-brand-border bg-white pl-5 pr-14 text-body-md text-text-primary outline-none transition focus:border-brand-primary focus:ring-4 focus:ring-brand-surface"
            placeholder={`${selectedCategory.label} 정책 조건을 입력하세요...`}
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
