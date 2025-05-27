import sqlite3, json, time
from typing import List, Dict, Optional, Tuple
class SQLiteConversationStore:
    def __init__(self, db_path: str = "conversations.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        # now includes user_id
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            timestamp       REAL NOT NULL,
            metadata        TEXT
        );
        """)
        self.conn.commit()

    def get_conn(self):
        """
        Return the underlying sqlite3 connection.
        """
        return self.conn

    def get_conversations(self, user_id: str) -> List[Tuple]:
        """
        Return rows of (conversation_id, title, message_count, last_active)
        for this user, ordered by last_active DESC.
        """
        conn = self.get_conn()
        
    def add_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO messages
              (user_id, conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
              user_id,
              conversation_id,
              role,
              content,
              time.time(),
              json.dumps(metadata or {})
            )
        )
        self.conn.commit()

    def get_messages(
        self,
        user_id: str,
        conversation_id: str
    ) -> List[Dict]:
        cur = self.conn.execute(
            """
            SELECT role, content, metadata
            FROM messages
            WHERE user_id = ? AND conversation_id = ?
            ORDER BY timestamp
            """,
            (user_id, conversation_id)
        )
        rows = cur.fetchall()
        return [
            {"role": r, "content": c, "metadata": json.loads(m or "{}")}
            for r, c, m in rows
        ]

    def get_conversations(self, user_id: str) -> List[Tuple]:
        """
        Return rows of (conversation_id, title, message_count, last_active)
        for this user, ordered by last_active DESC.
        """
        conn = self.get_conn()
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
        return rows

    def bulk_add_messages(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict]
    ) -> None:
        batch = [
            (
              user_id,
              conversation_id,
              m["role"],
              m["content"],
              m["timestamp"],
              json.dumps(m.get("metadata", {}))
            )
            for m in messages
        ]
        self.conn.executemany(
            """
            INSERT INTO messages
              (user_id, conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            batch
        )
        self.conn.commit()