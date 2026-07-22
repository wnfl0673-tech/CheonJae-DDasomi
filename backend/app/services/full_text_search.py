"""정확 일치(Ctrl+F 스타일) 태그 검색.

임베딩 기반 의미 유사도 검색은 "관련 있어 보이지만" 실제로는 해당 태그
문자열이 없는 페이지를 근거로 제시할 수 있다. 이를 보완하기 위해 인덱싱된
청크 텍스트 전체에서 태그 문자열이 실제로 등장하는 페이지를 정확히 찾고,
PyMuPDF로 해당 페이지 내 정확한 위치(bounding box)까지 계산한다.
"""

import re
from typing import Dict, List, Tuple

import fitz  # PyMuPDF

from app.services import vector_store

# (file_name, page_number) -> 해당 페이지에 속한 청크 텍스트를 이어붙인 문자열
_PAGE_TEXT_CACHE: Dict[Tuple[str, int], str] = {}
_PAGE_PATH_CACHE: Dict[str, str] = {}  # file_name -> pdf_path

# "PIT-7541A", "I-LG-541-002" 처럼 문자+숫자가 하이픈으로 이어진 설비 태그 패턴
_TAG_PATTERN = re.compile(r"\b[A-Za-z]{1,6}(?:-[A-Za-z0-9]{1,8}){1,4}\b")

MAX_MATCHED_PAGES = 15


def extract_tag_candidates(question: str) -> List[str]:
    """질문 문장에서 설비 태그로 보이는 토큰(예: PIT-7541A)을 추출한다."""
    seen = set()
    tags = []
    for match in _TAG_PATTERN.finditer(question):
        tag = match.group(0)
        if not any(ch.isdigit() for ch in tag):  # 숫자 없는 순수 단어는 태그가 아닐 확률이 높음
            continue
        key = tag.upper()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def rebuild_cache() -> None:
    """ChromaDB에 저장된 청크 텍스트로부터 페이지 단위 전문 검색 캐시를 재구성한다.

    서버 시작 시, 그리고 /api/index로 문서가 추가/변경될 때마다 호출한다.
    """
    global _PAGE_TEXT_CACHE, _PAGE_PATH_CACHE

    collection = vector_store.get_collection()
    if collection.count() == 0:
        _PAGE_TEXT_CACHE = {}
        _PAGE_PATH_CACHE = {}
        return

    result = collection.get(include=["documents", "metadatas"])

    page_text: Dict[Tuple[str, int], List[str]] = {}
    path_map: Dict[str, str] = {}

    for text, meta in zip(result["documents"], result["metadatas"]):
        if not meta:
            continue
        file_name = meta.get("file_name")
        page_number = meta.get("page_number")
        pdf_path = meta.get("pdf_path")
        if not file_name or page_number is None:
            continue

        page_text.setdefault((file_name, page_number), []).append(text)
        if pdf_path:
            path_map[file_name] = pdf_path

    _PAGE_TEXT_CACHE = {key: "\n".join(parts) for key, parts in page_text.items()}
    _PAGE_PATH_CACHE = path_map


def find_tag_occurrences(tag: str) -> List[dict]:
    """태그 문자열이 실제로 등장하는 모든 (파일, 페이지)를 찾아 정확한 좌표와 함께 반환한다."""
    if not _PAGE_TEXT_CACHE:
        rebuild_cache()

    tag_upper = tag.upper()
    matches: List[dict] = []

    for (file_name, page_number), text in _PAGE_TEXT_CACHE.items():
        if tag_upper not in text.upper():
            continue

        pdf_path = _PAGE_PATH_CACHE.get(file_name)
        if not pdf_path:
            continue

        rects, page_width, page_height = _find_rects_on_page(pdf_path, page_number, tag)

        matches.append(
            {
                "tag": tag,
                "file_name": file_name,
                "page_number": page_number,
                "pdf_path": pdf_path,
                "rects": rects,
                "page_width": page_width,
                "page_height": page_height,
            }
        )

        if len(matches) >= MAX_MATCHED_PAGES:
            break

    matches.sort(key=lambda m: (m["file_name"], m["page_number"]))
    return matches


# CAD 툴(AutoCAD 등)에서 변환된 도면 PDF는 글자 메트릭이 깨져 있어, PyMuPDF가
# 계산한 단어 bounding box가 실제 텍스트 길이보다 훨씬 작게(예: 9글자인데 3pt) 나오는
# 경우가 있다. 이 경우 하이라이트 사각형이 화면에서 점처럼 보여 실질적으로 안 보인다.
# 태그 길이에 비해 비정상적으로 작은 박스는 중심을 유지한 채 최소 크기로 보정한다.
_MIN_CHAR_SPAN = 4.0  # 글자당 최소 예상 길이(pt)
_MIN_THICKNESS = 8.0  # 하이라이트 박스의 최소 두께(pt)


def _normalize_rect(x0: float, y0: float, x1: float, y1: float, tag_len: int) -> List[float]:
    width, height = x1 - x0, y1 - y0
    expected = max(tag_len * _MIN_CHAR_SPAN, _MIN_THICKNESS)

    if height >= width:  # 세로 방향 텍스트로 추정 — 세로를 글자 길이만큼, 가로를 두께만큼 보정
        if height < expected:
            cy = (y0 + y1) / 2
            y0, y1 = cy - expected / 2, cy + expected / 2
        if width < _MIN_THICKNESS:
            cx = (x0 + x1) / 2
            x0, x1 = cx - _MIN_THICKNESS / 2, cx + _MIN_THICKNESS / 2
    else:  # 가로 방향 텍스트로 추정
        if width < expected:
            cx = (x0 + x1) / 2
            x0, x1 = cx - expected / 2, cx + expected / 2
        if height < _MIN_THICKNESS:
            cy = (y0 + y1) / 2
            y0, y1 = cy - _MIN_THICKNESS / 2, cy + _MIN_THICKNESS / 2

    return [x0, y0, x1, y1]


def _find_rects_on_page(pdf_path: str, page_number: int, tag: str):
    """PyMuPDF로 특정 페이지에서 태그 문자열의 정확한 bounding box를 찾는다."""
    try:
        with fitz.open(pdf_path) as doc:
            page = doc[page_number - 1]
            page_rect = page.rect

            rects = []
            seen_coords = set()
            for candidate in (tag, tag.upper(), tag.lower()):
                for r in page.search_for(candidate):
                    coord = (round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1))
                    if coord in seen_coords:
                        continue
                    seen_coords.add(coord)
                    rects.append(_normalize_rect(r.x0, r.y0, r.x1, r.y1, len(tag)))

            return rects, page_rect.width, page_rect.height
    except Exception:
        return [], 0.0, 0.0
