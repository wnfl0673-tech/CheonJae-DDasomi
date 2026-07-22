from fastapi import APIRouter

from app.schemas import StatusResponse
from app.services import vector_store

router = APIRouter()


@router.get("/api/status", response_model=StatusResponse)
def get_status():
    """실제 인덱싱 현황을 반환한다 (프론트엔드 하단 통계 표시용)."""
    stats = vector_store.get_stats()
    return StatusResponse(**stats)
