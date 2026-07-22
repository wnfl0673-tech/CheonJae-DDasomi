"use client";

import { useEffect, useState } from "react";
import { deleteConversation, getConversations } from "@/lib/api";
import { ConversationSummary } from "@/types";

interface HistoryPanelProps {
  onSelectConversation: (id: string) => void;
}

function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "방금 전";
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}시간 전`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}일 전`;
  return date.toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
}

export default function HistoryPanel({ onSelectConversation }: HistoryPanelProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    getConversations()
      .then(setConversations)
      .catch((err) => setError(err instanceof Error ? err.message : "불러오기 실패"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    if (!confirm("이 대화 기록을 삭제할까요?")) return;
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch {
      alert("삭제에 실패했습니다.");
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden max-w-3xl mx-auto w-full p-lg">
      <h2 className="font-display-lg text-headline-md text-on-surface mb-md">대화 기록</h2>

      {loading && <p className="text-on-tertiary-container font-body-sm">불러오는 중...</p>}
      {error && <p className="text-error font-body-sm">{error}</p>}
      {!loading && !error && conversations.length === 0 && (
        <p className="text-on-tertiary-container font-body-sm">
          아직 저장된 대화가 없습니다. 챗봇에 질문을 입력하면 여기에 자동으로 기록됩니다.
        </p>
      )}

      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-sm">
        {conversations.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelectConversation(c.id)}
            className="w-full text-left industrial-border bg-surface-container-low hover:bg-surface-container-high rounded-lg p-md flex items-center justify-between gap-md transition-colors group"
          >
            <div className="min-w-0 flex-1">
              <p className="font-body-base text-on-surface font-semibold truncate">{c.title}</p>
              <p className="text-[11px] text-on-tertiary-container mt-0.5">
                {formatRelativeTime(c.updated_at)} · 메시지 {c.message_count}개
              </p>
            </div>
            <span
              onClick={(e) => handleDelete(e, c.id)}
              className="material-symbols-outlined text-on-tertiary-container hover:text-error opacity-0 group-hover:opacity-100 transition-opacity shrink-0 text-[20px]"
              title="삭제"
            >
              delete
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
