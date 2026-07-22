"use client";

import { useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import DocManagementPanel from "@/components/DocManagementPanel";
import EmptyState from "@/components/EmptyState";
import HistoryPanel from "@/components/HistoryPanel";
import PdfViewer from "@/components/PdfViewer";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import {
  getConversationDetail,
  getFaultCasePdfUrl,
  getHealth,
  getPdfUrl,
  getStatus,
  sendChatMessage,
  triggerFaultCaseIndexing,
  triggerIndexing,
} from "@/lib/api";
import { ChatMessageData, FaultCaseMatch, SourceItem, StatusResponse, TagMatch } from "@/types";

let idCounter = 0;
function nextId() {
  idCounter += 1;
  return `msg-${idCounter}`;
}

function generateConversationId(): string {
  return `conv-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export default function Home() {
  const [view, setView] = useState<"chat" | "history" | "docs">("chat");
  const [conversationId, setConversationId] = useState<string>(() => generateConversationId());
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [indexMessage, setIndexMessage] = useState<string | null>(null);
  const [indexingFaultCases, setIndexingFaultCases] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);

  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [fileSource, setFileSource] = useState<"main" | "fault_case">("main");
  const [pageNumber, setPageNumber] = useState<number>(1);

  useEffect(() => {
    const check = () => {
      getHealth().then(setHealthy);
      getStatus()
        .then(setStatus)
        .catch(() => setStatus(null));
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  function handleSourceSelect(source: SourceItem) {
    setFileSource("main");
    setSelectedFileName(source.file_name);
    setPageNumber(source.page_number);
  }

  function handleTagMatchSelect(match: TagMatch) {
    setFileSource("main");
    setSelectedFileName(match.file_name);
    setPageNumber(match.page_number);
  }

  function handleFaultCaseOpen(match: FaultCaseMatch) {
    if (match.document_type !== "pdf") return; // HWP는 다운로드 링크로 별도 처리됨
    setFileSource("fault_case");
    setSelectedFileName(match.source_file);
    setPageNumber(1);
  }

  function handleNewChat() {
    setMessages([]);
    setInput("");
    setSelectedFileName(null);
    setFileSource("main");
    setPageNumber(1);
    setConversationId(generateConversationId());
    setView("chat");
  }

  function handleHistoryClick() {
    setView("history");
  }

  function handleDocsClick() {
    setView("docs");
  }

  async function handleSelectConversation(id: string) {
    try {
      const detail = await getConversationDetail(id);
      const restored: ChatMessageData[] = [];
      let lastSource: SourceItem | null = null;
      let lastTagMatch: TagMatch | null = null;

      for (const m of detail.messages) {
        restored.push({ id: nextId(), role: "user", question: m.question });
        if (m.answer) {
          restored.push({ id: nextId(), role: "assistant", response: m.answer });
          if (m.answer.exact_tag_matches.length > 0) {
            lastTagMatch = m.answer.exact_tag_matches[0];
            lastSource = null;
          } else if (m.answer.sources.length > 0) {
            lastSource = m.answer.sources[0];
            lastTagMatch = null;
          }
        } else if (m.error) {
          restored.push({ id: nextId(), role: "assistant", error: m.error });
        }
      }

      setMessages(restored);
      setConversationId(id);
      setInput("");
      if (lastTagMatch) {
        handleTagMatchSelect(lastTagMatch);
      } else if (lastSource) {
        handleSourceSelect(lastSource);
      } else {
        setSelectedFileName(null);
        setFileSource("main");
        setPageNumber(1);
      }
      setView("chat");
    } catch (err) {
      alert(err instanceof Error ? err.message : "대화를 불러오지 못했습니다.");
    }
  }

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { id: nextId(), role: "user", question }]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendChatMessage(question, conversationId);
      setConversationId(response.conversation_id);
      setMessages((prev) => [...prev, { id: nextId(), role: "assistant", response }]);
      if (response.exact_tag_matches.length > 0) {
        handleTagMatchSelect(response.exact_tag_matches[0]);
      } else if (response.sources.length > 0) {
        handleSourceSelect(response.sources[0]);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.";
      setMessages((prev) => [...prev, { id: nextId(), role: "assistant", error: message }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleIndex() {
    setIndexing(true);
    setIndexMessage(null);
    try {
      const result = await triggerIndexing();
      setIndexMessage(result.message);
      getStatus()
        .then(setStatus)
        .catch(() => {});
    } catch {
      setIndexMessage("인덱싱 중 오류가 발생했습니다.");
    } finally {
      setIndexing(false);
    }
  }

  async function handleIndexFaultCases() {
    setIndexingFaultCases(true);
    setIndexMessage(null);
    try {
      const result = await triggerFaultCaseIndexing();
      setIndexMessage(result.message);
    } catch {
      setIndexMessage("고장사례 인덱싱 중 오류가 발생했습니다.");
    } finally {
      setIndexingFaultCases(false);
    }
  }

  const lastAssistantResponse = [...messages].reverse().find((m) => m.role === "assistant" && m.response)?.response;
  const lastAssistantSources = lastAssistantResponse?.sources ?? [];
  const lastAssistantTagMatches = lastAssistantResponse?.exact_tag_matches ?? [];

  return (
    <div className="min-h-screen bg-background text-on-background">
      <Sidebar
        onNewChat={handleNewChat}
        onHistoryClick={handleHistoryClick}
        onDocsClick={handleDocsClick}
        activeView={view}
      />
      <main className="ml-64 flex flex-col h-screen overflow-hidden">
        <TopBar
          healthy={healthy}
          onIndex={handleIndex}
          indexing={indexing}
          indexMessage={indexMessage}
          onIndexFaultCases={handleIndexFaultCases}
          indexingFaultCases={indexingFaultCases}
        />
        {view === "docs" ? (
          <DocManagementPanel />
        ) : view === "history" ? (
          <HistoryPanel onSelectConversation={handleSelectConversation} />
        ) : messages.length === 0 ? (
          <EmptyState value={input} onChange={setInput} onSend={handleSend} loading={loading} status={status} />
        ) : (
          <div className="flex-1 flex overflow-hidden">
            <ChatPanel
              messages={messages}
              input={input}
              onInputChange={setInput}
              onSend={handleSend}
              loading={loading}
              onSourceSelect={handleSourceSelect}
              onTagMatchSelect={handleTagMatchSelect}
              onFaultCaseOpen={handleFaultCaseOpen}
            />
            <PdfViewer
              fileUrl={
                selectedFileName
                  ? fileSource === "fault_case"
                    ? getFaultCasePdfUrl(selectedFileName)
                    : getPdfUrl(selectedFileName)
                  : null
              }
              fileName={selectedFileName}
              pageNumber={pageNumber}
              onPageNumberChange={setPageNumber}
              sources={lastAssistantSources}
              onSourceSelect={handleSourceSelect}
              tagMatches={lastAssistantTagMatches}
              onTagMatchSelect={handleTagMatchSelect}
            />
          </div>
        )}
      </main>
    </div>
  );
}
