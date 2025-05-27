# backend/app/core/redis_client.py

import redis.asyncio as aioredis
import json
import time
from typing import List, Tuple, Dict, Optional
from ..config import settings

"""
Redis client module.

Provides a global `redis_client` instance for caching conversation history,
top-k question counters, and any other Redis-based caching needs.
Configuration is driven by the `REDIS_URL` setting in `config.py`.
"""

redis_client = aioredis.Redis.from_url(
    str(settings.REDIS_URL),
    encoding="utf-8",
    decode_responses=True
)


# -- Conversation History Hot-Cache --

async def cache_chat_message(user_id: str, conversation_id: str, role: str, content: str, timestamp: float = None):
    key = f"chat:{user_id}:{conversation_id}:history"
    payload = json.dumps({
        "role": role,
        "content": content,
        "timestamp": timestamp or time.time()
    })

    # Pipeline LPUSH, LTRIM, and EXPIRE in one round-trip
    pipe = redis_client.pipeline()
    await pipe.lpush(key, payload)
    await pipe.ltrim(key, 0, settings.MAX_CACHE_LENGTH - 1)
    await pipe.expire(key, settings.CACHE_TTL_SECONDS)
    await pipe.execute()


async def get_cached_messages(
    user_id: str,
    conversation_id: str
) -> List[Dict]:
    """
    Retrieve cached conversation history, oldest-first.
    Returns empty list if no cache exists.
    """
    key = f"chat:{user_id}:{conversation_id}:history"
    raw = await redis_client.lrange(key, 0, -1)
    if not raw:
        return []
    # raw is newest->oldest; reverse for chronological
    msgs = [json.loads(item) for item in reversed(raw)]
    return msgs


# -- Top-K Question Counters --

def increment_question(api_id: str, question: str) -> None:
    """
    Increment the count for a question under a specific API.
    """
    key = f"topk:questions:{api_id}"
    redis_client.zincrby(key, 1, question)


def get_topk_questions(
    api_id: str,
    k: int = 10
) -> List[Tuple[str, int]]:
    """
    Return the top-k most frequently asked questions for the given API.
    """
    key = f"topk:questions:{api_id}"
    items = redis_client.zrevrange(key, 0, k - 1, withscores=True)
    # Convert scores to int
    return [(q, int(score)) for q, score in items]