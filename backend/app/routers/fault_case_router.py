import logging
from pathlib import Path
from typing import List, Tuple
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas import (
    DeleteResponse,
    FaultCaseFileInfo,
    FaultCaseFileListResponse,
    UploadQueuedResponse,
)
from app.services import fault_case_processor, fault_case_store, pdf_processor

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_FAULT_CASE_EXTENSIONS = {".pdf", ".hwp", ".xlsx"}
MAX_UPLOAD_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


def _index_document_case(path: Path, source_type: str, raw_text: str) -> fault_case_processor.FaultCase:
    """PDF/HWP 원문 텍스트에서 라벨 기반 정규식(LLM 미사용)으로 필드를 추출해 FaultCase로 변환한다."""
    fields = fault_case_processor.extract_fields_heuristic(raw_text)
    site = fault_case_processor.parse_site_from_filename(path.name) or "미상"
    occurrence_date = fault_case_processor.parse_date_from_filename(path.name)
    title = fields.get("title") or path.stem
    summary = (
        f"{title}\n"
        f"증상: {fields.get('symptom', '')}\n"
        f"원인: {fields.get('cause', '')}\n"
        f"조치: {fields.get('action_taken', '')}"
    )
    return fault_case_processor.FaultCase(
        case_id=f"{source_type}::{path.name}",
        source_type=source_type,
        site=site,
        equipment_tag=fields.get("equipment_tag", ""),
        occurrence_date=occurrence_date,
        title=title,
        summary=summary,
        pdf_path=str(path),
        source_file=path.name,
    )


def _index_uploaded_fault_case_file(path: Path) -> Tuple[int, List[str]]:
    """업로드된 파일 한 개를 확장자에 따라 인덱싱한다. (추가된 사례 수, 오류 목록)을 반환."""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        case_id = f"pdf::{path.name}"
        if fault_case_store.case_exists(case_id):
            return 0, []
        try:
            pages = pdf_processor.extract_pages(path)
            raw_text = "\n".join(p.text for p in pages)
            if not raw_text.strip():
                return 0, [f"{path.name}: 텍스트를 추출하지 못했습니다 (스캔 이미지일 수 있음)."]
            case = _index_document_case(path, "pdf", raw_text)
            fault_case_store.add_fault_cases([case])
            return 1, []
        except Exception as exc:  # noqa: BLE001
            return 0, [f"{path.name}: {exc}"]

    if suffix == ".hwp":
        case_id = f"hwp::{path.name}"
        if fault_case_store.case_exists(case_id):
            return 0, []
        try:
            raw_text = fault_case_processor.extract_hwp_text(path)
            if not raw_text.strip():
                return 0, [f"{path.name}: 텍스트를 추출하지 못했습니다."]
            case = _index_document_case(path, "hwp", raw_text)
            fault_case_store.add_fault_cases([case])
            return 1, []
        except Exception as exc:  # noqa: BLE001
            return 0, [f"{path.name}: {exc}"]

    if suffix == ".xlsx":
        try:
            records = fault_case_processor.load_excel_records(path)
        except Exception as exc:  # noqa: BLE001
            return 0, [f"{path.name}: {exc}"]

        new_cases = []
        for row in records:
            case_id = f"excel::{path.name}::{row['row_index']}"
            if fault_case_store.case_exists(case_id):
                continue
            title = row["title"] or row["description"][:40]
            summary = (
                f"{title}\n"
                f"설비: {row['equipment']} / 기기명: {row['equipment_tag']}\n"
                f"내용: {row['description']}"
            )
            new_cases.append(
                fault_case_processor.FaultCase(
                    case_id=case_id,
                    source_type="excel",
                    site=row["site"] or "미상",
                    equipment_tag=row["equipment_tag"],
                    occurrence_date=row["occurrence_date"],
                    title=title,
                    summary=summary,
                    pdf_path=None,
                    source_file=path.name,
                )
            )
        if new_cases:
            fault_case_store.add_fault_cases(new_cases)
        return len(new_cases), []

    return 0, [f"{path.name}: 지원하지 않는 파일 형식입니다."]


@router.post("/api/index-fault-cases", response_model=UploadQueuedResponse)
def index_fault_cases(background_tasks: BackgroundTasks):
    """타지사 고장사례 폴더(PDF + HWP + 엑셀)를 읽어 fault_cases 컬렉션에 추가한다.

    이미 추가된 사례(case_id 기준)는 건너뛴다. 파일이 많거나 크면 오래 걸릴 수 있어
    실제 인덱싱은 백그라운드에서 진행하고, 이 응답은 바로 반환된다. GET /api/fault-cases를
    다시 호출해 진행 상황(case_count)을 확인한다.
    """
    pdf_paths = fault_case_processor.discover_fault_case_pdfs(settings.fault_case_dir)
    hwp_paths = fault_case_processor.discover_fault_case_hwps(settings.fault_case_dir)
    excel_paths = fault_case_processor.discover_fault_case_excels(settings.fault_case_dir)
    all_paths = pdf_paths + hwp_paths + excel_paths

    if not all_paths:
        return UploadQueuedResponse(
            queued_files=[], message=f"'{settings.fault_case_dir}' 폴더에 파일이 없습니다."
        )

    background_tasks.add_task(_index_fault_case_files_in_background, all_paths)
    message = f"{len(all_paths)}개 파일 인덱싱을 백그라운드에서 시작했습니다. 잠시 후 목록을 새로고침해 확인하세요."
    return UploadQueuedResponse(queued_files=[p.name for p in all_paths], message=message)


@router.get("/api/fault-case-pdf/{filename}")
def get_fault_case_pdf(filename: str):
    """고장사례 폴더(프로젝트 밖 경로)에서 PDF를 찾아 서빙한다."""
    safe_name = Path(filename).name  # 경로 조작 방지
    match = next(settings.fault_case_dir.rglob(safe_name), None)
    if not match or not match.exists() or match.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail=f"고장사례 PDF를 찾을 수 없습니다: {safe_name}")

    # 파일명에 한글 등 비-ASCII 문자가 있으면 Content-Disposition 헤더는
    # latin-1로만 인코딩 가능하므로 RFC 5987 filename* 형식을 사용한다.
    return FileResponse(
        path=match,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(safe_name)}"},
    )


@router.get("/api/fault-case-hwp/{filename}")
def get_fault_case_hwp(filename: str):
    """HWP 원본 파일을 다운로드로 제공한다 (브라우저에서 미리보기는 지원하지 않음)."""
    safe_name = Path(filename).name
    match = next(settings.fault_case_dir.rglob(safe_name), None)
    if not match or not match.exists() or match.suffix.lower() != ".hwp":
        raise HTTPException(status_code=404, detail=f"HWP 파일을 찾을 수 없습니다: {safe_name}")

    return FileResponse(
        path=match,
        media_type="application/x-hwp",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(safe_name)}"},
    )


@router.get("/api/fault-case-excel/{filename}")
def get_fault_case_excel(filename: str):
    """고장현황 overview 엑셀 원본을 다운로드로 제공한다 (엑셀 행 기반 고장사례의 근거 파일)."""
    safe_name = Path(filename).name
    match = next(settings.fault_case_dir.rglob(safe_name), None)
    if not match or not match.exists() or match.suffix.lower() != ".xlsx":
        raise HTTPException(status_code=404, detail=f"엑셀 파일을 찾을 수 없습니다: {safe_name}")

    return FileResponse(
        path=match,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(safe_name)}"},
    )


@router.get("/api/fault-cases", response_model=FaultCaseFileListResponse)
def list_fault_case_files():
    """Doc Management 탭에 표시할 고장사례(PDF/HWP/엑셀) 파일 목록을 반환한다."""
    counts = fault_case_store.count_cases_by_source_file()

    files: List[FaultCaseFileInfo] = []
    for path in fault_case_processor.discover_fault_case_pdfs(settings.fault_case_dir):
        files.append(
            FaultCaseFileInfo(
                file_name=path.name, source_type="pdf", size_bytes=path.stat().st_size, case_count=counts.get(path.name, 0)
            )
        )
    for path in fault_case_processor.discover_fault_case_hwps(settings.fault_case_dir):
        files.append(
            FaultCaseFileInfo(
                file_name=path.name, source_type="hwp", size_bytes=path.stat().st_size, case_count=counts.get(path.name, 0)
            )
        )
    for path in fault_case_processor.discover_fault_case_excels(settings.fault_case_dir):
        files.append(
            FaultCaseFileInfo(
                file_name=path.name,
                source_type="excel",
                size_bytes=path.stat().st_size,
                case_count=counts.get(path.name, 0),
            )
        )

    return FaultCaseFileListResponse(files=files)


def _index_fault_case_files_in_background(paths: List[Path]) -> None:
    """대용량 PDF/HWP 인덱싱이 요청 제한시간을 넘기지 않도록 응답 이후 백그라운드에서 처리."""
    for path in paths:
        try:
            _index_uploaded_fault_case_file(path)
        except Exception:  # noqa: BLE001 - 백그라운드 작업 실패가 서버를 죽이지 않도록
            logger.exception("백그라운드 고장사례 인덱싱 실패: %s", path.name)


@router.post("/api/fault-cases/upload", response_model=UploadQueuedResponse)
async def upload_fault_cases(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """Doc Management 탭에서 업로드한 고장사례(PDF/HWP/엑셀)를 저장하고, 인덱싱은 백그라운드로 넘긴다.

    GET /api/fault-cases를 잠시 후 다시 호출하면 case_count 값이 채워진 것으로
    완료 여부를 확인할 수 있다.
    """
    queued: list[str] = []
    errors: list[str] = []
    saved_paths: list[Path] = []

    for upload in files:
        safe_name = Path(upload.filename or "").name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in ALLOWED_FAULT_CASE_EXTENSIONS:
            errors.append(f"{safe_name}: PDF/HWP/엑셀 파일만 업로드할 수 있습니다.")
            continue

        content = await upload.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            errors.append(f"{safe_name}: 파일 크기가 너무 큽니다 (최대 {settings.max_upload_size_mb}MB).")
            continue

        dest = settings.fault_case_dir / safe_name
        dest.write_bytes(content)
        saved_paths.append(dest)
        queued.append(safe_name)

    if saved_paths:
        background_tasks.add_task(_index_fault_case_files_in_background, saved_paths)

    message = f"{len(queued)}개 파일 업로드 완료. 백그라운드에서 인덱싱 중이니 잠시 후 목록을 새로고침해 확인하세요."
    if errors:
        message += f" 오류 {len(errors)}건."

    return UploadQueuedResponse(queued_files=queued, message=message, errors=errors)


@router.delete("/api/fault-cases/{filename}", response_model=DeleteResponse)
def delete_fault_case_file(filename: str):
    """업로드된 고장사례 파일을 디스크와 벡터DB에서 삭제한다."""
    safe_name = Path(filename).name
    match = next(settings.fault_case_dir.rglob(safe_name), None)
    if not match or not match.exists():
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {safe_name}")

    fault_case_store.delete_cases_by_source_file(safe_name)
    match.unlink()

    return DeleteResponse(message=f"{safe_name} 삭제 완료")
