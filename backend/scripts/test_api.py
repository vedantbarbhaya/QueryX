# backend/scripts/test_api.py

import os
import glob
import subprocess
import time
import sqlite3
import redis
from datetime import datetime

import requests

# Base URL of your running FastAPI server
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
# Redis client for synchronous checks
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def tail_log(lines: int = 20):
    """Print the last `lines` from the most recent application log."""
    script_dir = os.path.dirname(__file__)
    log_dir = os.path.abspath(os.path.join(script_dir, "..", "app", "logs"))
    pattern = os.path.join(log_dir, "app_*.log")
    files = glob.glob(pattern)
    if not files:
        print("No log files found")
        return
    latest = max(files, key=os.path.getmtime)
    print(f"\n=== Last {lines} lines from log: {latest} ===")
    output = subprocess.check_output(["tail", f"-n{lines}", latest])
    print(output.decode())

def call_health():
    print("== Health Check ==")
    r = requests.get(f"{BASE_URL}/health")
    print(r.status_code, r.text)

def call_documents():
    print("\n== List Documents ==")
    r = requests.get(f"{BASE_URL}/api/documents")
    try:
        print(r.status_code, r.json())
    except ValueError:
        print(r.status_code, r.text)

def call_chat(message: str, conversation_id: str = None, user_id: str = None):
    print(f"\n== Chat: {message!r} ==")
    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    if user_id:
        payload["user_id"] = user_id

    r = requests.post(f"{BASE_URL}/api/chat", json=payload)
    try:
        data = r.json()
    except ValueError:
        data = r.text
    print(r.status_code, data)
    return data if isinstance(data, dict) else {}

def check_redis_history(user_id: str, conv_id: str, min_len: int = 1):
    key = f"chat:{user_id}:{conv_id}:history"
    length = redis_client.llen(key)
    print(f"Redis list {key} length = {length}")
    assert length >= min_len, f"Expected >= {min_len} items in Redis cache, got {length}"

def check_sqlite_rows(conv_id: str, min_rows: int = 1):
    # Resolve path to root/conversations.db (where the app actually writes)
    db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "conversations.db")
    )
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,))
    count = cur.fetchone()[0]
    conn.close()
    print(f"SQLite has {count} rows for conversation {conv_id}")
    assert count >= min_rows, f"Expected >= {min_rows} rows in SQLite, got {count}"


def main():
    print(f"🔍 Starting API test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    call_health()

    # 1️⃣ Direct greeting
    resp = call_chat("hello")
    conv_id = resp.get("conversation_id")
    user_id = resp.get("user_id")

    # Immediately verify Redis hot-cache got it
    check_redis_history(user_id, conv_id, min_len=1)

    # 2️⃣ Ask for documentation prompt
    resp = call_chat("add documentation", conv_id, user_id)
    check_redis_history(user_id, conv_id, min_len=2)

    # 3️⃣ Provide a docs URL
    resp = call_chat("https://petstore.swagger.io/v2/swagger.json", conv_id, user_id)
    check_redis_history(user_id, conv_id, min_len=3)

    # 4️⃣ Optional: list loaded documents
    call_documents()

    # 5️⃣ Give the outbox flusher time to persist messages
    print("\n⏳ Waiting 6 seconds for outbox flush...")
    time.sleep(6)
    # After flush, check that SQLite has at least the 3 messages we sent
    check_sqlite_rows(conv_id, min_rows=3)

    # 6️⃣ RAG-powered question
    resp = call_chat("How do I authenticate with the Petstore API?", conv_id, user_id)
    check_redis_history(user_id, conv_id, min_len=4)

    # 7️⃣ Wait again for any background flush
    print("\n⏳ Waiting another 6 seconds for outbox flush...")
    time.sleep(6)
    # Now SQLite should have 4+ rows
    check_sqlite_rows(conv_id, min_rows=4)

    # 8️⃣ Tail the latest logs to see performance & storage entries
    tail_log()

    # 9️⃣ List conversations for this user
    print("\n== List Conversations ==")
    r = requests.get(
        f"{BASE_URL}/api/conversations",
        params={"user_id": user_id},
    )
    print(r.status_code, r.json())
    assert r.status_code == 200, "Conversations endpoint should return 200"
    convs = r.json()
    # We should have at least one conversation summary
    assert isinstance(convs, list) and len(convs) >= 1, "Expected ≥1 conversation returned"
    # Basic shape check
    first = convs[0]
    for field in ("conversation_id", "title", "message_count", "last_active", "last_active_readable"):
        assert field in first, f"Missing field {field} in conversation summary"

    print("\n✅ Conversations endpoint OK")

    print("\n✅ All checks passed")

if __name__ == "__main__":
    main()