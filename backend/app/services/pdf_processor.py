"""PDF 텍스트 추출 및 청크 분할.

대용량(1GB급) PDF 확장을 고려해 파일을 페이지 단위로 스트리밍 처리한다.
PyMuPDF(fitz)는 페이지를 필요한 시점에만 로드하므로 파일 전체를 메모리에
올리지 않고도 순차 처리가 가능하다.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List

import fitz  # PyMuPDF


@dataclass
class PageText:
    page_number: int  # 1-based
    text: str


@dataclass
class Chunk:
    chunk_id: str
    file_name: str
    page_number: int
    text: str
    pdf_path: str


def compute_file_hash(pdf_path: Path) -> str:
    """파일 내용 기반 해시. 재인덱싱 여부 판단(증분 인덱싱)에 사용."""
    hasher = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            hasher.update(block)
    return hasher.hexdigest()[:16]


def extract_pages(pdf_path: Path) -> List[PageText]:
    """PDF에서 페이지 단위로 텍스트를 추출한다."""
    pages: List[PageText] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages.append(PageText(page_number=i + 1, text=text))
    return pages


def split_into_chunks(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> List[str]:
    """단순 문자 길이 기준 슬라이딩 윈도우 청크 분할.

    해커톤 MVP 수준에서는 문장 경계보다 속도/단순성을 우선한다.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(text):
        chunk = text[start : start + chunk_size]
        chunks.append(chunk)
        start += step
    return chunks


def process_pdf(pdf_path: Path, chunk_size: int, overlap: int) -> List[Chunk]:
    """PDF 한 개를 페이지 추출 -> 청크 분할까지 처리해 Chunk 리스트로 반환."""
    file_name = pdf_path.name
    pages = extract_pages(pdf_path)

    chunks: List[Chunk] = []
    for page in pages:
        page_chunks = split_into_chunks(page.text, chunk_size, overlap)
        for idx, chunk_text in enumerate(page_chunks):
            chunk_id = f"{file_name}::p{page.page_number}::c{idx}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    file_name=file_name,
                    page_number=page.page_number,
                    text=chunk_text,
                    pdf_path=str(pdf_path),
                )
            )
    return chunks
