import { useState } from "react";
import { ChatArea } from "../components/ChatArea";
import { PolicyGraph } from "../components/PolicyGraph";
import { Sidebar } from "../components/Sidebar";

export function ChatbotPage() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <main className="min-h-screen bg-brand-background text-text-primary">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
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
