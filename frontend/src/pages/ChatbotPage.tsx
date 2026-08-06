import { useState } from "react";
import { ChatArea } from "../components/ChatArea";
import { PolicyGraph } from "../components/PolicyGraph";
import { Sidebar } from "../components/Sidebar";
import { categories } from "../data/policies";
import type { SessionGraphResponse } from "../shared/api/chatbot";

type ChatbotPageProps = {
  currentPath: "/" | "/chatbot";
  onNavigate: (path: "/" | "/chatbot", hash?: string) => void;
};

export function ChatbotPage({ currentPath, onNavigate }: ChatbotPageProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState(categories[0]?.id ?? "housing");
  const [sessionGraph, setSessionGraph] = useState<SessionGraphResponse | null>(null);

  return (
    <main className="min-h-screen bg-[#dfe8e1] text-text-primary">
      <Sidebar collapsed={collapsed} currentPath={currentPath} onNavigate={onNavigate} onToggle={() => setCollapsed((value) => !value)} />
      <div
        className={`grid h-screen grid-cols-1 gap-6 overflow-hidden p-6 transition-[margin-left] duration-300 ease-sidebar xl:grid-cols-[minmax(380px,0.86fr)_minmax(560px,1.14fr)] ${
          collapsed ? "ml-20" : "ml-[260px]"
        }`}
      >
        <ChatArea
          selectedCategoryId={selectedCategoryId}
          sessionGraph={sessionGraph}
          onCategoryChange={setSelectedCategoryId}
          onGraphChange={setSessionGraph}
        />
        <PolicyGraph selectedCategoryId={selectedCategoryId} sessionGraph={sessionGraph} />
      </div>
    </main>
  );
}
