"use client";

import { ChatMessageData, FaultCaseMatch, SourceItem, TagMatch } from "@/types";
import ChatMessage from "./ChatMessage";
import DdasomiLoading from "./DdasomiLoading";

interface ChatPanelProps {
  messages: ChatMessageData[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  loading: boolean;
  onSourceSelect: (source: SourceItem) => void;
  onTagMatchSelect: (match: TagMatch) => void;
  onFaultCaseOpen: (match: FaultCaseMatch) => void;
}

export default function ChatPanel({
  messages,
  input,
  onInputChange,
  onSend,
  loading,
  onSourceSelect,
  onTagMatchSelect,
  onFaultCaseOpen,
}: ChatPanelProps) {
  return (
    <section className="w-[45%] flex flex-col border-r border-outline-variant bg-surface-dim relative min-w-[380px]">
      <div className="flex-1 overflow-y-auto p-md custom-scrollbar space-y-lg">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            onSourceClick={onSourceSelect}
            onTagMatchClick={onTagMatchSelect}
            onFaultCaseOpen={onFaultCaseOpen}
          />
        ))}
        {loading && <DdasomiLoading />}
      </div>

      <div className="p-md bg-surface border-t border-outline-variant shrink-0">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
            className="w-full bg-surface-container border border-outline-variant rounded-xl p-md pr-14 text-on-surface placeholder:text-on-tertiary-container focus:ring-1 focus:ring-secondary focus:border-secondary outline-none resize-none transition-all"
            placeholder="Ask Ttasome for technical guidance..."
            rows={2}
          />
          <button
            onClick={onSend}
            disabled={loading || !input.trim()}
            className="absolute bottom-3 right-3 w-10 h-10 bg-secondary-container text-on-secondary-container rounded-lg flex items-center justify-center hover:scale-105 active:scale-95 transition-transform shadow-lg disabled:opacity-40 disabled:hover:scale-100"
          >
            <span className="material-symbols-outlined">send</span>
          </button>
        </div>
        <p className="mt-xs text-[10px] text-on-tertiary-container text-center italic">
          AI 응답에는 오류가 포함될 수 있습니다. 실제 작업 전 반드시 승인된 절차와 교차 확인하세요.
        </p>
      </div>
    </section>
  );
}
