import { useState } from "react";
import { ChatArea } from "../components/ChatArea";
import { PolicyGraph } from "../components/PolicyGraph";
import { Sidebar } from "../components/Sidebar";

type ChatbotPageProps = {
  currentPath: "/" | "/chatbot";
  onNavigate: (path: "/" | "/chatbot", hash?: string) => void;
};

export function ChatbotPage({ currentPath, onNavigate }: ChatbotPageProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <main className="min-h-screen bg-[#dfe8e1] text-text-primary">
      <Sidebar collapsed={collapsed} currentPath={currentPath} onNavigate={onNavigate} onToggle={() => setCollapsed((value) => !value)} />
      <div
        className={`grid h-screen grid-cols-1 gap-6 overflow-hidden p-6 transition-[margin-left] duration-300 ease-sidebar xl:grid-cols-[minmax(380px,0.86fr)_minmax(560px,1.14fr)] ${
          collapsed ? "ml-20" : "ml-[260px]"
        }`}
      >
        <ChatArea />
        <PolicyGraph />
      </div>
    </main>
  );
}
