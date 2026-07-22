import {
  ChatResponse,
  ConversationDetail,
  ConversationSummary,
  DocumentFileInfo,
  DocumentUploadResponse,
  FaultCaseFileInfo,
  FaultCaseUploadResponse,
  StatusResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function sendChatMessage(question: string, conversationId?: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "답변 생성에 실패했습니다.");
  }

  return res.json();
}

export async function getConversations(): Promise<ConversationSummary[]> {
  const res = await fetch(`${API_BASE}/api/history/conversations`);
  if (!res.ok) {
    throw new Error("대화 기록을 불러오지 못했습니다.");
  }
  return res.json();
}

export async function getConversationDetail(conversationId: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/api/history/conversations/${encodeURIComponent(conversationId)}`);
  if (!res.ok) {
    throw new Error("대화 내용을 불러오지 못했습니다.");
  }
  return res.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/history/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("대화 삭제에 실패했습니다.");
  }
}

export async function triggerIndexing(): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/index`, { method: "POST" });
  if (!res.ok) {
    throw new Error("문서 인덱싱에 실패했습니다.");
  }
  return res.json();
}

export function getPdfUrl(fileName: string): string {
  return `${API_BASE}/api/pdf/${encodeURIComponent(fileName)}`;
}

export function getFaultCasePdfUrl(fileName: string): string {
  return `${API_BASE}/api/fault-case-pdf/${encodeURIComponent(fileName)}`;
}

export function getFaultCaseHwpUrl(fileName: string): string {
  return `${API_BASE}/api/fault-case-hwp/${encodeURIComponent(fileName)}`;
}

export function getFaultCaseExcelUrl(fileName: string): string {
  return `${API_BASE}/api/fault-case-excel/${encodeURIComponent(fileName)}`;
}

export async function triggerFaultCaseIndexing(): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/index-fault-cases`, { method: "POST" });
  if (!res.ok) {
    throw new Error("고장사례 인덱싱에 실패했습니다.");
  }
  return res.json();
}

export async function getStatus(): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) {
    throw new Error("상태 조회에 실패했습니다.");
  }
  return res.json();
}

export async function listDocuments(): Promise<DocumentFileInfo[]> {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) {
    throw new Error("문서 목록을 불러오지 못했습니다.");
  }
  const data = await res.json();
  return data.files;
}

export async function uploadDocuments(files: File[]): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_BASE}/api/documents`, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "문서 업로드에 실패했습니다.");
  }
  return res.json();
}

export async function deleteDocument(fileName: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(fileName)}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error("문서 삭제에 실패했습니다.");
  }
}

export async function listFaultCaseFiles(): Promise<FaultCaseFileInfo[]> {
  const res = await fetch(`${API_BASE}/api/fault-cases`);
  if (!res.ok) {
    throw new Error("고장사례 파일 목록을 불러오지 못했습니다.");
  }
  const data = await res.json();
  return data.files;
}

export async function uploadFaultCaseFiles(files: File[]): Promise<FaultCaseUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_BASE}/api/fault-cases/upload`, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "고장사례 업로드에 실패했습니다.");
  }
  return res.json();
}

export async function deleteFaultCaseFile(fileName: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/fault-cases/${encodeURIComponent(fileName)}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error("고장사례 파일 삭제에 실패했습니다.");
  }
}

export async function getHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
