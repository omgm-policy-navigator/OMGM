import { Bell, ChevronLeft, ChevronRight, Heart, Home, LogOut, Menu, MessageCircle, Settings } from "lucide-react";

type SidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
  currentPath: "/" | "/chatbot";
  onNavigate: (path: "/" | "/chatbot", hash?: string) => void;
};

const menuItems = [
  { label: "Dashboard", icon: Home, path: "/" as const },
  { label: "Chatbot", icon: MessageCircle, path: "/chatbot" as const, hash: "chat" },
  { label: "My Policy", icon: Heart, path: "/chatbot" as const, hash: "chat" },
  { label: "Notifications", icon: Bell, path: "/chatbot" as const, hash: "chat" },
];

export function Sidebar({ collapsed, currentPath, onNavigate, onToggle }: SidebarProps) {
  return (
    <aside
      className={`fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-brand-border bg-white transition-[width] duration-300 ease-sidebar ${
        collapsed ? "w-20" : "w-[260px]"
      }`}
      aria-label="사이드바"
    >
      <button
        type="button"
        onClick={onToggle}
        className="absolute right-[-12px] top-6 z-50 flex h-8 w-8 items-center justify-center rounded-full border border-brand-border bg-white text-text-secondary shadow-card transition hover:bg-brand-surface hover:text-brand-primary"
        aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>

      <div className={`flex h-20 items-center gap-3 px-5 ${collapsed ? "justify-center" : ""}`}>
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-primary text-white">
          <Heart size={22} fill="currentColor" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <h1 className="truncate text-h4">나만 결혼해?!</h1>
            <p className="truncate text-caption text-text-secondary">Policy Navigator</p>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => onNavigate("/chatbot", "chat")}
        className={`mx-4 mb-6 flex h-12 items-center justify-center gap-3 rounded-xl bg-brand-primary text-body-md text-white transition duration-200 hover:brightness-90 active:scale-95 ${
          collapsed ? "px-0" : "px-4"
        }`}
      >
        <Menu size={20} />
        {!collapsed && <span>Start New Chat</span>}
      </button>

      <nav className="flex flex-1 flex-col gap-2 px-4">
        {menuItems.map(({ label, icon: Icon, path, hash }) => {
          const active = currentPath === path && (path !== "/chatbot" || label === "Chatbot");
          return (
            <button
              type="button"
              onClick={() => onNavigate(path, hash)}
              key={label}
              className={`flex h-12 items-center gap-3 rounded-xl px-4 py-3 text-left text-body-sm transition ${
                active ? "bg-brand-primary text-white" : "text-text-secondary hover:bg-brand-surface hover:text-text-primary"
              } ${collapsed ? "justify-center px-0" : ""}`}
              title={collapsed ? label : undefined}
            >
              <Icon size={20} />
              {!collapsed && <span>{label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-brand-border p-4">
        {[{ label: "Settings", icon: Settings }, { label: "Logout", icon: LogOut }].map(({ label, icon: Icon }) => (
          <a
            href="#chat"
            key={label}
            className={`mb-2 flex h-11 items-center gap-3 rounded-xl px-4 text-body-sm text-text-secondary transition hover:bg-brand-surface hover:text-text-primary ${
              collapsed ? "justify-center px-0" : ""
            }`}
            title={collapsed ? label : undefined}
          >
            <Icon size={19} />
            {!collapsed && <span>{label}</span>}
          </a>
        ))}
      </div>
    </aside>
  );
}
