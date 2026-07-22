from fastapi import APIRouter, HTTPException

from app.schemas import ConversationDetail, ConversationSummary, HistoryMessage
from app.services import history_store

router = APIRouter()


@router.get("/api/history/conversations", response_model=list[ConversationSummary])
def list_conversations():
    """모든 대화 스레드 목록을 최신순으로 반환한다."""
    return [ConversationSummary(**c) for c in history_store.list_conversations()]


@router.get("/api/history/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str):
    """특정 대화 스레드의 전체 메시지를 반환한다."""
    messages = history_store.get_conversation_messages(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="대화 기록을 찾을 수 없습니다.")
    return ConversationDetail(
        id=conversation_id,
        messages=[HistoryMessage(**m) for m in messages],
    )


@router.delete("/api/history/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    history_store.delete_conversation(conversation_id)
    return {"status": "ok"}
