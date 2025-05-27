

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from pydantic import BaseModel
from datetime import datetime
from ..core.conversation_store import SQLiteConversationStore
from ..config import settings


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    message_count: int
    last_active: float
    last_active_readable: str


store = SQLiteConversationStore("conversations.db")
router = APIRouter()


@router.get("/api/conversations", response_model=List[ConversationSummary])
def list_conversations(user_id: str = Query(..., description="User ID whose conversations to list")):
    """
    List all conversations for a given user, returning summary info for each.
    """
    # Try to use store.get_conversations(user_id), else fallback to raw SQL.
    try:
        # Try to call a method if it exists
        if hasattr(store, "get_conversations"):
            rows = store.get_conversations(user_id)
        else:
            # Fallback: run raw SQL
            conn = store.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT conversation_id,
                       MAX(CASE WHEN role='user' THEN content ELSE NULL END) AS title,
                       COUNT(*) AS message_count,
                       MAX(timestamp) AS last_active
                FROM messages
                WHERE user_id = ?
                GROUP BY conversation_id
                ORDER BY last_active DESC
            """, (user_id,))
            rows = cur.fetchall()
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch conversations: {str(e)}")

    summaries = []
    for row in rows:
        # Support both tuple and dict/row types
        conversation_id = row[0]
        title = row[1] if row[1] else "New Conversation"
        message_count = row[2]
        last_active = float(row[3]) if row[3] is not None else 0.0
        last_active_readable = (
            datetime.fromtimestamp(last_active).strftime('%Y-%m-%d %H:%M:%S')
            if last_active else ""
        )
        summaries.append(ConversationSummary(
            conversation_id=conversation_id,
            title=title,
            message_count=message_count,
            last_active=last_active,
            last_active_readable=last_active_readable
        ))
    return summaries