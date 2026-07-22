"use client";

interface TopBarProps {
  healthy: boolean | null;
  onIndex: () => void;
  indexing: boolean;
  indexMessage: string | null;
  onIndexFaultCases: () => void;
  indexingFaultCases: boolean;
}

export default function TopBar({
  healthy,
  onIndex,
  indexing,
  indexMessage,
  onIndexFaultCases,
  indexingFaultCases,
}: TopBarProps) {
  const statusLabel = healthy === null ? "확인 중" : healthy ? "AI 서비스 정상" : "백엔드 연결 끊김";
  const dotColor = healthy === null ? "bg-outline" : healthy ? "bg-green-500 animate-pulse" : "bg-red-500";

  return (
    <header className="flex justify-between items-center w-full px-lg py-md h-16 bg-background border-b border-outline-variant shrink-0">
      <div className="flex items-center gap-xl min-w-0">
        <span className="text-headline-md font-headline-md font-extrabold text-secondary shrink-0">천재 따소미!!</span>
        <nav className="hidden md:flex gap-lg items-center min-w-0">
          <span className="font-label-caps text-label-caps text-secondary border-b-2 border-secondary pb-1 shrink-0">
            New Chat
          </span>
          {indexMessage && (
            <span className="font-body-sm text-on-surface-variant truncate">{indexMessage}</span>
          )}
        </nav>
      </div>
      <div className="flex items-center gap-md shrink-0">
        <button
          onClick={onIndex}
          disabled={indexing}
          className="flex items-center gap-1 text-on-surface-variant hover:text-secondary transition-colors disabled:opacity-50 border border-outline-variant rounded-lg px-sm py-1"
          title="documents 폴더의 PDF를 다시 인덱싱합니다"
        >
          <span className={"material-symbols-outlined text-[16px] " + (indexing ? "animate-spin" : "")}>
            {indexing ? "progress_activity" : "sync"}
          </span>
          <span className="font-label-caps text-label-caps">{indexing ? "인덱싱 중" : "문서 인덱싱"}</span>
        </button>
        <button
          onClick={onIndexFaultCases}
          disabled={indexingFaultCases}
          className="flex items-center gap-1 text-on-surface-variant hover:text-secondary transition-colors disabled:opacity-50 border border-outline-variant rounded-lg px-sm py-1"
          title="타지사 고장사례 폴더(PDF+엑셀)를 다시 인덱싱합니다"
        >
          <span className={"material-symbols-outlined text-[16px] " + (indexingFaultCases ? "animate-spin" : "")}>
            {indexingFaultCases ? "progress_activity" : "history"}
          </span>
          <span className="font-label-caps text-label-caps">
            {indexingFaultCases ? "고장사례 인덱싱 중" : "고장사례 인덱싱"}
          </span>
        </button>
        <div className="flex items-center gap-sm bg-surface-container px-sm py-1 rounded-full border border-outline-variant">
          <div className={"w-2 h-2 rounded-full " + dotColor} />
          <span className="text-[10px] font-label-caps text-on-surface uppercase tracking-wider">{statusLabel}</span>
        </div>
      </div>
    </header>
  );
}
