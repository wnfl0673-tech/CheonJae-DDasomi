import uuid

from fastapi import APIRouter, HTTPException

from app.schemas import ChatRequest, ChatResponse, FaultCaseMatch, SourceItem, TagMatch
from app.services import answer_builder, fault_case_processor, fault_case_store, full_text_search, history_store, vector_store

router = APIRouter()

# cosine distance가 이보다 크면(=관련성이 낮으면) 근거로 채택하지 않는다.
RELEVANCE_DISTANCE_THRESHOLD = 1.1
FAULT_CASE_DISTANCE_THRESHOLD = 1.2
FAULT_CASE_TOP_K = 3


@router.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """사용자 질문을 받아 관련 PDF 페이지를 검색한다 (LLM 미사용, 검색 결과만 반환)."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="질문을 입력해주세요.")

    conversation_id = request.conversation_id or str(uuid.uuid4())

    hits = vector_store.query(question, top_k=request.top_k)
    relevant_hits = [h for h in hits if h["distance"] <= RELEVANCE_DISTANCE_THRESHOLD]

    # 의미 유사도 검색과 별개로, 질문에 포함된 태그(예: PIT-7541A)가 실제로
    # 등장하는 페이지를 Ctrl+F 방식으로 정확히 찾는다. 유사도 검색은 "관련 있어
    # 보이지만" 실제 태그가 없는 페이지를 근거로 제시할 수 있어 이를 보완한다.
    tag_candidates = full_text_search.extract_tag_candidates(question)
    exact_matches: list[dict] = []
    for tag in tag_candidates:
        exact_matches.extend(full_text_search.find_tag_occurrences(tag))

    # 타지사 과거 고장사례 중 이번 질문과 관련된 사례를 찾는다. "최근/최신"처럼 날짜순
    # 정렬을 요구하는 질문은 의미 유사도 검색으로는 정확한 최신 사례를 보장할 수 없으므로
    # occurrence_date 기준 정렬 결과를 사용한다.
    if fault_case_processor.is_recency_query(question):
        relevant_fault_hits = fault_case_store.get_recent_fault_cases(top_k=FAULT_CASE_TOP_K)
    else:
        fault_hits = fault_case_store.query_fault_cases(question, top_k=FAULT_CASE_TOP_K)
        relevant_fault_hits = [h for h in fault_hits if h["distance"] <= FAULT_CASE_DISTANCE_THRESHOLD]

    sections = answer_builder.build_answer_sections(question, relevant_hits, exact_matches, tag_candidates)

    sources = _build_sources(relevant_hits)
    fault_case_matches = _build_fault_case_matches(relevant_fault_hits)

    response = ChatResponse(
        question=question,
        answer_sections=sections,
        sources=sources,
        has_document_evidence=len(sources) > 0 or len(exact_matches) > 0,
        exact_tag_matches=[TagMatch(**m) for m in exact_matches],
        similar_fault_cases=fault_case_matches,
        conversation_id=conversation_id,
    )

    history_store.save_exchange(conversation_id, question, answer=response.model_dump(), error=None)

    return response


def _distance_to_similarity(distance: float) -> int:
    """cosine distance(0~2, 낮을수록 유사)를 대략적인 0~100 유사도 점수로 변환.

    참고용 근사치이며 보정된 확률이 아니다.
    """
    similarity = max(0.0, min(1.0, 1 - distance / 2))
    return round(similarity * 100)


def _build_fault_case_matches(hits: list[dict]) -> list[FaultCaseMatch]:
    matches = []
    for h in hits:
        source_type = h.get("source_type", "")
        document_type = source_type if source_type in ("pdf", "hwp", "excel") else "none"
        matches.append(
            FaultCaseMatch(
                case_id=h["case_id"],
                title=h.get("title", ""),
                site=h.get("site", ""),
                equipment_tag=h.get("equipment_tag", ""),
                occurrence_date=h.get("occurrence_date", ""),
                summary=h.get("summary", ""),
                similarity=_distance_to_similarity(h["distance"]),
                source_file=h.get("source_file", ""),
                has_document=document_type != "none",
                document_type=document_type,
            )
        )
    matches.sort(key=lambda m: m.similarity, reverse=True)
    return matches


def _build_sources(hits: list[dict]) -> list[SourceItem]:
    """같은 파일/페이지 중복을 제거하고 유사도 순으로 정렬한 SourceItem 목록으로 변환한다."""
    seen: set[tuple[str, int]] = set()
    sources: list[SourceItem] = []

    for h in hits:
        key = (h["file_name"], h["page_number"])
        if key in seen:
            continue
        seen.add(key)

        snippet = h["text"][:200] + ("..." if len(h["text"]) > 200 else "")
        sources.append(
            SourceItem(
                file_name=h["file_name"],
                page_number=h["page_number"],
                chunk_id=h["chunk_id"],
                pdf_path=h["pdf_path"],
                snippet=snippet,
                similarity=_distance_to_similarity(h["distance"]),
            )
        )

    sources.sort(key=lambda s: s.similarity, reverse=True)
    return sources
