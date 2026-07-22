from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter()


@router.get("/api/pdf/{filename}")
def get_pdf(filename: str):
    """documents 폴더의 PDF 파일을 프론트엔드 미리보기용으로 제공한다."""
    safe_name = Path(filename).name  # 경로 조작(path traversal) 방지
    pdf_path = settings.documents_dir / safe_name

    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail=f"PDF 파일을 찾을 수 없습니다: {safe_name}")

    # 파일명에 한글 등 비-ASCII 문자가 있으면 Content-Disposition 헤더는
    # latin-1로만 인코딩 가능하므로 RFC 5987 filename* 형식을 사용한다.
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(safe_name)}"},
    )
