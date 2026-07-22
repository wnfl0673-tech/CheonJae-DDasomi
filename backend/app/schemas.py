from typing import List, Optional

from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    file_name: str
    page_number: int
    chunk_id: str
    pdf_path: str
    snippet: str
    similarity: int = Field(description="벡터 검색 유사도 (0~100, 참고용 근사치)")


class ChatRequest(BaseModel):
    question: str
    top_k: Optional[int] = None
    conversation_id: Optional[str] = Field(
        default=None, description="대화 스레드 ID. 없으면 서버가 새로 발급한다."
    )


class TagMatch(BaseModel):
    tag: str = Field(description="검색된 태그 문자열 (예: PIT-7541A)")
    file_name: str
    page_number: int
    pdf_path: str
    rects: List[List[float]] = Field(
        description="태그가 실제로 발견된 페이지 내 좌표 [x0,y0,x1,y1] 목록 (PDF 포인트 단위)"
    )
    page_width: float
    page_height: float


class AnswerSections(BaseModel):
    document_based_findings: str = Field(description="문서 기반 확인사항")
    maintenance_actions: str = Field(description="유지보수 조치사항")
    possible_causes: str = Field(description="가능한 원인")
    precautions: str = Field(description="주의사항 (작업허가/안전조치/담당자 확인 문구 포함)")
    general_recommendations: Optional[str] = Field(
        default=None, description="일반 점검 권고사항 (문서 근거가 부족할 때)"
    )


class FaultCaseMatch(BaseModel):
    case_id: str
    title: str
    site: str
    equipment_tag: str
    occurrence_date: str
    summary: str
    similarity: int = Field(description="벡터 검색 유사도 (0~100, 참고용 근사치)")
    source_file: str
    has_document: bool = Field(description="열람 가능한 원본 문서가 있는지 여부")
    document_type: str = Field(
        default="none",
        description="원본 문서 형식: 'pdf'(미리보기 가능) | 'hwp'(다운로드만 가능) | 'excel'(다운로드만 가능) | 'none'",
    )


class ChatResponse(BaseModel):
    question: str
    answer_sections: AnswerSections
    sources: List[SourceItem]
    has_document_evidence: bool
    exact_tag_matches: List[TagMatch] = Field(
        default_factory=list,
        description="질문에서 추출한 태그가 실제로(Ctrl+F 방식) 발견된 페이지 목록",
    )
    similar_fault_cases: List[FaultCaseMatch] = Field(
        default_factory=list, description="유사한 과거 타지사 고장사례 목록"
    )
    conversation_id: str = Field(description="이 대화가 속한 스레드 ID")


class IndexedFileInfo(BaseModel):
    file_name: str
    pages: int
    chunks: int


class IndexResponse(BaseModel):
    indexed_files: List[IndexedFileInfo]
    skipped_files: List[str]
    total_chunks_added: int
    message: str
    errors: List[str] = Field(default_factory=list)


class DocumentFileInfo(BaseModel):
    file_name: str
    size_bytes: int
    chunks: int
    pages: int


class DocumentListResponse(BaseModel):
    files: List[DocumentFileInfo]


class DeleteResponse(BaseModel):
    message: str


class UploadQueuedResponse(BaseModel):
    """업로드 직후 응답. 인덱싱은 백그라운드에서 진행되며, 목록 API를 다시 조회하면
    chunks/case_count가 채워지는 것으로 완료 여부를 확인할 수 있다."""

    queued_files: List[str]
    message: str
    errors: List[str] = Field(default_factory=list)


class FaultCaseFileInfo(BaseModel):
    file_name: str
    source_type: str  # pdf | hwp | excel
    size_bytes: int
    case_count: int


class FaultCaseFileListResponse(BaseModel):
    files: List[FaultCaseFileInfo]


class StatusResponse(BaseModel):
    total_chunks: int
    total_files: int


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class HistoryMessage(BaseModel):
    question: str
    answer: Optional[ChatResponse] = None
    error: Optional[str] = None
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    messages: List[HistoryMessage]


class FaultCaseIndexResponse(BaseModel):
    added: int
    skipped: int
    errors: List[str]
    message: str
