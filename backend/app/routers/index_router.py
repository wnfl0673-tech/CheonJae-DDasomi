from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas import (
    DeleteResponse,
    DocumentFileInfo,
    DocumentListResponse,
    IndexedFileInfo,
    IndexResponse,
)
from app.services import full_text_search, pdf_processor, vector_store

router = APIRouter()

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf"}
MAX_UPLOAD_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


def _index_single_pdf(pdf_path: Path) -> Optional[IndexedFileInfo]:
    """PDF 한 개를 증분 인덱싱한다. 이미 동일 해시로 인덱싱되어 있으면 None을 반환(스킵)."""
    file_hash = pdf_processor.compute_file_hash(pdf_path)

    if vector_store.is_file_up_to_date(pdf_path.name, file_hash):
        return None

    vector_store.delete_file_chunks(pdf_path.name)

    chunks = pdf_processor.process_pdf(
        pdf_path,
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )
    added = vector_store.add_chunks(chunks, file_hash)
    pages = len({c.page_number for c in chunks})
    return IndexedFileInfo(file_name=pdf_path.name, pages=pages, chunks=added)


@router.post("/api/index", response_model=IndexResponse)
def index_documents():
    """backend/documents 폴더의 PDF를 읽어 텍스트를 추출하고 ChromaDB에 저장한다.

    이미 동일한 내용(해시)으로 인덱싱된 파일은 건너뛴다 (증분 인덱싱).
    """
    pdf_files = sorted(settings.documents_dir.glob("*.pdf"))

    indexed: list[IndexedFileInfo] = []
    skipped: list[str] = []
    total_chunks = 0

    for pdf_path in pdf_files:
        result = _index_single_pdf(pdf_path)
        if result is None:
            skipped.append(pdf_path.name)
        else:
            indexed.append(result)
            total_chunks += result.chunks

    if indexed:
        full_text_search.rebuild_cache()

    if not pdf_files:
        message = f"'{settings.documents_dir}' 폴더에 PDF 파일이 없습니다. PDF를 추가한 뒤 다시 호출하세요."
    else:
        message = f"인덱싱 완료: {len(indexed)}개 파일 처리, {len(skipped)}개 파일 스킵(변경 없음)."

    return IndexResponse(
        indexed_files=indexed,
        skipped_files=skipped,
        total_chunks_added=total_chunks,
        message=message,
    )


@router.get("/api/documents", response_model=DocumentListResponse)
def list_documents():
    """Doc Management 탭에 표시할 기술문서(PDF) 목록과 인덱싱 현황을 반환한다."""
    indexed = vector_store.list_indexed_files()
    files = [
        DocumentFileInfo(
            file_name=path.name,
            size_bytes=path.stat().st_size,
            chunks=indexed.get(path.name, {}).get("chunks", 0),
            pages=indexed.get(path.name, {}).get("pages", 0),
        )
        for path in sorted(settings.documents_dir.glob("*.pdf"))
    ]
    return DocumentListResponse(files=files)


@router.post("/api/documents", response_model=IndexResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Doc Management 탭에서 업로드한 PDF를 저장하고 즉시 인덱싱한다."""
    indexed: list[IndexedFileInfo] = []
    skipped: list[str] = []
    errors: list[str] = []
    total_chunks = 0

    for upload in files:
        safe_name = Path(upload.filename or "").name
        if Path(safe_name).suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
            errors.append(f"{safe_name}: PDF 파일만 업로드할 수 있습니다.")
            continue

        content = await upload.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            errors.append(f"{safe_name}: 파일 크기가 너무 큽니다 (최대 {settings.max_upload_size_mb}MB).")
            continue

        dest = settings.documents_dir / safe_name
        dest.write_bytes(content)

        try:
            result = _index_single_pdf(dest)
        except Exception as exc:  # noqa: BLE001 - 개별 파일 실패가 전체 업로드를 막지 않도록
            errors.append(f"{safe_name}: {exc}")
            continue

        if result is None:
            skipped.append(safe_name)
        else:
            indexed.append(result)
            total_chunks += result.chunks

    if indexed:
        full_text_search.rebuild_cache()

    message = f"업로드 완료: {len(indexed)}개 파일 인덱싱, {len(skipped)}개 스킵(변경 없음)."
    if errors:
        message += f" 오류 {len(errors)}건."

    return IndexResponse(
        indexed_files=indexed,
        skipped_files=skipped,
        total_chunks_added=total_chunks,
        message=message,
        errors=errors,
    )


@router.delete("/api/documents/{filename}", response_model=DeleteResponse)
def delete_document(filename: str):
    """업로드된 기술문서(PDF)를 디스크와 벡터DB에서 삭제한다."""
    safe_name = Path(filename).name
    path = settings.documents_dir / safe_name
    if not path.exists() or path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {safe_name}")

    vector_store.delete_file_chunks(safe_name)
    path.unlink()
    full_text_search.rebuild_cache()

    return DeleteResponse(message=f"{safe_name} 삭제 완료")
