from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.config import settings
from app.schemas import (
    DeleteResponse,
    DocumentFileInfo,
    DocumentListResponse,
    IndexedFileInfo,
    UploadQueuedResponse,
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


@router.post("/api/index", response_model=UploadQueuedResponse)
def index_documents(background_tasks: BackgroundTasks):
    """backend/documents 폴더의 PDF를 읽어 텍스트를 추출하고 ChromaDB에 저장한다.

    이미 동일한 내용(해시)으로 인덱싱된 파일은 건너뛴다 (증분 인덱싱). 대용량 PDF가
    섞여 있으면 오래 걸릴 수 있어 실제 인덱싱은 백그라운드에서 진행하고, 이 응답은
    바로 반환된다. GET /api/documents를 다시 호출해 진행 상황을 확인한다.
    """
    pdf_files = sorted(settings.documents_dir.glob("*.pdf"))

    if not pdf_files:
        message = f"'{settings.documents_dir}' 폴더에 PDF 파일이 없습니다. PDF를 추가한 뒤 다시 호출하세요."
        return UploadQueuedResponse(queued_files=[], message=message)

    background_tasks.add_task(_index_pdfs_in_background, pdf_files)
    message = f"{len(pdf_files)}개 파일 인덱싱을 백그라운드에서 시작했습니다. 잠시 후 목록을 새로고침해 확인하세요."
    return UploadQueuedResponse(queued_files=[p.name for p in pdf_files], message=message)


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


def _index_pdfs_in_background(pdf_paths: List[Path]) -> None:
    """업로드 응답을 먼저 반환한 뒤 백그라운드 스레드에서 실행되는 인덱싱 작업.

    대용량 PDF(수백~수천 청크)는 임베딩 계산에 요청 제한시간(보통 30~60초)을 넘길 만큼
    오래 걸릴 수 있어, HTTP 요청 안에서 동기로 처리하면 배포 환경(Railway 등)의 프록시가
    연결을 강제 종료해버린다. 그래서 파일 저장까지만 요청 안에서 하고, 실제 인덱싱은
    응답 이후 백그라운드에서 진행한다.
    """
    indexed_any = False
    for pdf_path in pdf_paths:
        try:
            if _index_single_pdf(pdf_path) is not None:
                indexed_any = True
        except Exception:  # noqa: BLE001 - 백그라운드 작업 실패가 서버를 죽이지 않도록
            pass

    if indexed_any:
        full_text_search.rebuild_cache()


@router.post("/api/documents", response_model=UploadQueuedResponse)
async def upload_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """Doc Management 탭에서 업로드한 PDF를 저장하고, 인덱싱은 백그라운드로 넘긴다.

    응답에는 인덱싱 결과(청크 수 등)가 아직 반영되지 않는다. GET /api/documents를
    잠시 후 다시 호출하면 chunks/pages 값이 채워진 것으로 완료 여부를 확인할 수 있다.
    """
    queued: list[str] = []
    errors: list[str] = []
    saved_paths: list[Path] = []

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
        saved_paths.append(dest)
        queued.append(safe_name)

    if saved_paths:
        background_tasks.add_task(_index_pdfs_in_background, saved_paths)

    message = f"{len(queued)}개 파일 업로드 완료. 백그라운드에서 인덱싱 중이니 잠시 후 목록을 새로고침해 확인하세요."
    if errors:
        message += f" 오류 {len(errors)}건."

    return UploadQueuedResponse(queued_files=queued, message=message, errors=errors)


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
