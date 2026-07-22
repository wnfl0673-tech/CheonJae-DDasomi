"use client";

interface NavItemProps {
  icon: string;
  label: string;
  active?: boolean;
  comingSoon?: boolean;
  onClick?: () => void;
}

function NavItem({ icon, label, active, comingSoon, onClick }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      className={
        "w-full flex items-center gap-md px-md py-sm rounded-lg font-label-caps text-label-caps transition-colors " +
        (active
          ? "bg-secondary-container text-on-secondary-container font-bold"
          : "text-on-surface-variant hover:bg-surface-container-high")
      }
    >
      <span className="material-symbols-outlined text-[20px]">{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {comingSoon && (
        <span className="text-[9px] tracking-normal normal-case text-on-tertiary-container border border-outline-variant rounded px-1 py-0.5">
          준비중
        </span>
      )}
    </button>
  );
}

interface SidebarProps {
  onNewChat: () => void;
  onHistoryClick: () => void;
  onDocsClick: () => void;
  activeView: "chat" | "history" | "docs";
}

export default function Sidebar({ onNewChat, onHistoryClick, onDocsClick, activeView }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 flex flex-col p-md z-40 bg-surface-container border-r border-outline-variant">
      <button
        onClick={onNewChat}
        className="flex items-center gap-sm mb-lg px-xs text-left hover:opacity-80 transition-opacity"
      >
        <div className="w-9 h-9 rounded-lg bg-secondary-container flex items-center justify-center text-on-secondary-container shrink-0">
          <span className="material-symbols-outlined">bolt</span>
        </div>
        <div className="overflow-hidden">
          <h1 className="font-headline-md text-headline-md text-secondary leading-tight truncate">천재따소미</h1>
          <p className="font-label-caps text-[9px] text-on-tertiary-container tracking-widest uppercase">
            Power Systems AI
          </p>
        </div>
      </button>

      <button
        onClick={onNewChat}
        className="bg-secondary-container text-on-secondary-container rounded-lg py-sm px-lg font-bold flex items-center justify-center gap-sm mb-lg transition-transform active:scale-95 hover:brightness-110"
      >
        <span className="material-symbols-outlined text-[20px]">add_comment</span>
        <span className="font-label-caps text-label-caps">New Analysis</span>
      </button>

      <nav className="flex-1 space-y-1">
        <NavItem icon="add_comment" label="New Chat" active={activeView === "chat"} onClick={onNewChat} />
        <NavItem icon="description" label="Doc Management" active={activeView === "docs"} onClick={onDocsClick} />
        <NavItem icon="history" label="History" active={activeView === "history"} onClick={onHistoryClick} />
        <NavItem icon="settings" label="Settings" comingSoon />
        <NavItem icon="person" label="Profile" comingSoon />
      </nav>

      <div className="mt-auto pt-md border-t border-outline-variant">
        <NavItem icon="memory" label="System Status" comingSoon />
      </div>
    </aside>
  );
}
