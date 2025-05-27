# backend/app/core/message_queue.py

import json
import asyncio
import aio_pika
import pika
from typing import Dict, Optional
from ..config import settings
from ..utils.logger import logger

# === Configuration ===
RABBIT_URL = str(settings.RABBITMQ_URL)  # e.g. "amqp://guest:guest@localhost:5672/%2F"
EXCHANGE_NAME = "chat.outbox"
EXCHANGE_TYPE = "topic"
QUEUE_NAME = "chat.outbox.queue"    # bound to the exchange (topic semantics: routing_key patterns like "#" allowed)

# === Connection & Channel Setup (Async) ===
_aio_connection: aio_pika.RobustConnection = None
_aio_channel: aio_pika.Channel = None

async def get_aio_connection() -> aio_pika.RobustConnection:
    global _aio_connection
    if _aio_connection and not _aio_connection.is_closed:
        return _aio_connection
    _aio_connection = await aio_pika.connect_robust(str(settings.RABBITMQ_URL))
    return _aio_connection

async def get_aio_channel() -> aio_pika.Channel:
    global _aio_channel
    if _aio_channel and not _aio_channel.is_closed:
        return _aio_channel
    conn = await get_aio_connection()
    channel = await conn.channel()
    exch = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.bind(exch, routing_key="#")
    _aio_channel = channel
    return _aio_channel

# === Publisher API (Async) ===
async def publish_chat_message(
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict] = None
) -> None:
    """
    Publish one chat turn into RabbitMQ for durable outbox processing.
    """
    ch = await get_aio_channel()
    body = json.dumps({
        "user_id": user_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": __import__("time").time(),
        "metadata": metadata or {}
    }).encode()
    exch = await ch.get_exchange(EXCHANGE_NAME)
    await exch.publish(
        aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=conversation_id
    )
    logger.debug(f"Published message to RabbitMQ outbox: conv={conversation_id}, role={role}")

# === Close on Shutdown ===
def close_connection():
    global _channel, _connection
    try:
        if _channel and _channel.is_open:
            _channel.close()
        if _connection and _connection.is_open:
            _connection.close()
    except Exception as e:
        logger.warning(f"Error closing RabbitMQ connection: {e}")


# === Legacy Blocking I/O for OutboxFlusher ===
def get_connection():
    params = pika.URLParameters(RABBIT_URL)
    return pika.BlockingConnection(params)

def get_channel():
    conn = get_connection()
    ch = conn.channel()
    # declare exchange and queue for blocking consumer
    ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type=EXCHANGE_TYPE, durable=True)
    ch.queue_declare(queue=QUEUE_NAME, durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key="#")
    return ch