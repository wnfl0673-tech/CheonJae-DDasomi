from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    chat_router,
    fault_case_router,
    history_router,
    index_router,
    pdf_router,
    status_router,
)
from app.services import fault_case_store, full_text_search, history_store, vector_store

app = FastAPI(
    title="천재따소미 API",
    description="발전소 DCS 유지보수 AI 챗봇 백엔드",
    version="0.1.0",
)


@app.on_event("startup")
def load_embedding_model():
    """임베딩 모델을 메인 스레드에서 미리 로드한다.

    요청 스레드풀(worker thread)에서 최초 1회 로드할 경우 PyTorch가
    "Cannot copy out of meta tensor" 오류를 내는 환경이 있어(스레드 관련 이슈),
    서버 시작 시 메인 스레드에서 미리 초기화해 회피한다.
    """
    vector_store.get_collection()
    full_text_search.rebuild_cache()
    history_store.init_db()
    fault_case_store.get_fault_collection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(index_router.router, tags=["index"])
app.include_router(chat_router.router, tags=["chat"])
app.include_router(pdf_router.router, tags=["pdf"])
app.include_router(status_router.router, tags=["status"])
app.include_router(history_router.router, tags=["history"])
app.include_router(fault_case_router.router, tags=["fault-cases"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
