"""검색 결과만으로 답변 섹션을 구성한다 (LLM/외부 API 미사용).

보안성 검토 결과에 따라 외부 API 키를 사용할 수 없으므로, AI가 내용을 생성/추론하지
않고 검색된 문서 발췌·태그 정확 일치 결과를 그대로 정리해서 보여준다.
"""

from typing import List, Optional

from app.schemas import AnswerSections

_PRECAUTION_TEXT = "실제 작업 전 작업허가, 안전조치, 담당자 확인이 필요합니다."
_SNIPPET_MAX_LEN = 300


def _format_chunk(chunk: dict, index: int) -> str:
    snippet = chunk["text"].strip()
    if len(snippet) > _SNIPPET_MAX_LEN:
        snippet = snippet[:_SNIPPET_MAX_LEN] + "..."
    return f"[근거 {index}] {chunk['file_name']} ({chunk['page_number']}페이지)\n{snippet}"


def build_answer_sections(
    question: str,
    chunks: List[dict],
    exact_matches: Optional[List[dict]] = None,
    tag_candidates: Optional[List[str]] = None,
) -> AnswerSections:
    """검색된 결과만으로 답변 섹션을 구성한다. LLM 요약/추론은 수행하지 않는다.

    태그 정확 일치 결과와 과거 유사 고장사례는 프론트엔드에서 별도 카드로 이미
    보여주므로 여기서는 중복 서술하지 않고, 다른 곳에 없는 정보(태그 미발견 안내,
    문서 발췌 원문)만 정리한다.
    """
    exact_matches = exact_matches or []
    tag_candidates = tag_candidates or []

    findings_lines: List[str] = []

    if tag_candidates and not exact_matches:
        joined = ", ".join(f"'{t}'" for t in tag_candidates)
        findings_lines.append(f"{joined} 태그 문자열은 제공된 문서 전체에서 발견되지 않았습니다.")

    if chunks:
        findings_lines.extend(_format_chunk(c, i) for i, c in enumerate(chunks, 1))

    if not findings_lines:
        findings_lines.append("제공된 문서에서 관련 근거를 찾지 못했습니다.")

    return AnswerSections(
        document_based_findings="\n\n".join(findings_lines),
        maintenance_actions="",
        possible_causes="",
        precautions=_PRECAUTION_TEXT,
        general_recommendations=None,
    )
