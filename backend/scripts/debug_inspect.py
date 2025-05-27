# backend/scripts/debug_inspect.py

import json
import sqlite3
import redis
import pika
import os
import sys

# Ensure the project root (backend/) is on sys.path
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from app.config import settings 

def print_redis():
    print("=== Redis Cache ===")
    r = redis.Redis.from_url(str(settings.REDIS_URL), decode_responses=True)
    keys = r.keys("*")
    print(f"Found {len(keys)} keys:")
    for key in keys:
        t = r.type(key)
        print(f"- {key.decode() if isinstance(key, bytes) else key} (type: {t})")
        if t == "list":
            items = r.lrange(key, 0, -1)
            for i, item in enumerate(items):
                print(f"    [{i}] {item}")
        elif t == "zset":
            items = r.zrevrange(key, 0, -1, withscores=True)
            for member, score in items:
                print(f"    {member} → {int(score)}")
        else:
            val = r.get(key)
            print(f"    value → {val}")
    print()

def print_rabbitmq():
    print("=== RabbitMQ Outbox Queue ===")
    params = pika.URLParameters(str(settings.RABBITMQ_URL))
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    queue = "chat.outbox.queue"
    print(f"Peeking into queue '{queue}':")
    while True:
        method, props, body = ch.basic_get(queue=queue, auto_ack=False)
        if not method:
            print("  (no more messages)")
            break
        try:
            data = json.loads(body)
        except Exception:
            data = body.decode()
        print(f"  DeliveryTag={method.delivery_tag} → {data}")
        # requeue so we don't consume it
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    conn.close()
    print()

def print_sqlite():
    print("=== SQLite Message Store ===")
    db = sqlite3.connect("conversations.db")
    cur = db.cursor()
    cur.execute("""
        SELECT user_id, conversation_id, role, content, datetime(timestamp, 'unixepoch')
        FROM messages
        ORDER BY timestamp ASC
    """)
    rows = cur.fetchall()
    print(f"Retrieved {len(rows)} rows:")
    for user_id, conv_id, role, content, ts in rows:
        snippet = content if len(content) < 80 else content[:77] + "..."
        print(f"  [{ts}] ({conv_id[:8]} / {user_id[:8]}) {role}: {snippet}")
    db.close()
    print()

if __name__ == "__main__":
    print_redis()
    print_rabbitmq()
    print_sqlite()