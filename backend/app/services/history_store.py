"""대화 기록(History) 영구 저장.

SQLite 파일 하나로 대화 목록/메시지를 저장한다. 해커톤 MVP 규모에서는
별도 DB 서버 없이 이 정도로 충분하며, 필요 시 나중에 Postgres 등으로
교체해도 이 모듈의 함수 인터페이스는 그대로 유지할 수 있다.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, List, Optional

from app.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.history_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
            """
        )


def _make_title(question: str) -> str:
    title = question.strip().replace("\n", " ")
    return title[:40] + ("..." if len(title) > 40 else "")


def save_exchange(
    conversation_id: str,
    question: str,
    answer: Optional[dict],
    error: Optional[str],
) -> None:
    """질문 하나와 그에 대한 답변(또는 에러)을 기록에 남긴다."""
    now = _now()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conversation_id, _make_title(question), now, now),
            )
        else:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
            )

        conn.execute(
            """
            INSERT INTO messages (conversation_id, question, answer_json, error, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                question,
                json.dumps(answer, ensure_ascii=False) if answer is not None else None,
                error,
                now,
            ),
        )


def list_conversations() -> List[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at, COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_conversation_messages(conversation_id: str) -> List[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT question, answer_json, error, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
        messages = []
        for row in rows:
            messages.append(
                {
                    "question": row["question"],
                    "answer": json.loads(row["answer_json"]) if row["answer_json"] else None,
                    "error": row["error"],
                    "created_at": row["created_at"],
                }
            )
        return messages


def delete_conversation(conversation_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
