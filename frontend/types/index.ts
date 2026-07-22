export interface SourceItem {
  file_name: string;
  page_number: number;
  chunk_id: string;
  pdf_path: string;
  snippet: string;
  similarity: number;
}

export interface StatusResponse {
  total_chunks: number;
  total_files: number;
}

export interface TagMatch {
  tag: string;
  file_name: string;
  page_number: number;
  pdf_path: string;
  rects: number[][];
  page_width: number;
  page_height: number;
}

export interface AnswerSections {
  document_based_findings: string;
  maintenance_actions: string;
  possible_causes: string;
  precautions: string;
  general_recommendations?: string | null;
}

export interface FaultCaseMatch {
  case_id: string;
  title: string;
  site: string;
  equipment_tag: string;
  occurrence_date: string;
  summary: string;
  similarity: number;
  source_file: string;
  has_document: boolean;
  document_type: "pdf" | "hwp" | "excel" | "none";
}

export interface ChatResponse {
  question: string;
  answer_sections: AnswerSections;
  sources: SourceItem[];
  has_document_evidence: boolean;
  exact_tag_matches: TagMatch[];
  similar_fault_cases: FaultCaseMatch[];
  conversation_id: string;
}

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  question?: string;
  response?: ChatResponse;
  error?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface HistoryMessage {
  question: string;
  answer: ChatResponse | null;
  error: string | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  messages: HistoryMessage[];
}

export interface DocumentFileInfo {
  file_name: string;
  size_bytes: number;
  chunks: number;
  pages: number;
}

export interface DocumentUploadResponse {
  indexed_files: { file_name: string; pages: number; chunks: number }[];
  skipped_files: string[];
  total_chunks_added: number;
  message: string;
  errors: string[];
}

export interface FaultCaseFileInfo {
  file_name: string;
  source_type: "pdf" | "hwp" | "excel";
  size_bytes: number;
  case_count: number;
}

export interface FaultCaseUploadResponse {
  added: number;
  skipped: number;
  errors: string[];
  message: string;
}
