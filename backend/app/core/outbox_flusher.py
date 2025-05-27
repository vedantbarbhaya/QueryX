# backend/app/core/outbox_flusher.py

import threading
import time
import json
from collections import defaultdict

from .message_queue import get_channel, QUEUE_NAME
from .conversation_store import SQLiteConversationStore
from ..utils.logger import logger

class OutboxFlusher:
    """
    Background flusher that consumes messages from RabbitMQ outbox queue
    and bulk-inserts them into the SQLite messages table via the store.
    """

    def __init__(
        self,
        store: SQLiteConversationStore,
        batch_size: int = 10,
        poll_interval: float = 5.0
    ):
        self.store = store
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self._channel = get_channel()
        self._stop_event = threading.Event()

    def start(self):
        """
        Start the background thread for flushing.
        """
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        logger.info("OutboxFlusher started background thread")

    def stop(self):
        """
        Signal the flusher to stop and flush any remaining messages.
        """
        # Flush pending messages before stopping
        self.flush_once()
        self._stop_event.set()

    def _run(self):
        """
        Main loop: fetch up to batch_size messages, group by user/conversation,
        and bulk insert into SQLite, then sleep.
        """
        while not self._stop_event.is_set():
            self.flush_once()
            time.sleep(self.poll_interval)

    def flush_once(self):
        """
        Perform a single flush: fetch up to batch_size messages, group, and bulk insert.
        """
        start_cycle = time.monotonic()
        msgs = []
        for _ in range(self.batch_size):
            method, properties, body = self._channel.basic_get(
                queue=QUEUE_NAME,
                auto_ack=False
            )
            if method and body:
                try:
                    data = json.loads(body)
                    msgs.append(data)
                    self._channel.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Failed to parse or ack message: {e}", exc_info=True)
                    if method:
                        self._channel.basic_nack(
                            delivery_tag=method.delivery_tag, requeue=True
                        )
            else:
                break

        if msgs:
            # Group messages by (user_id, conversation_id)
            grouped = defaultdict(list)
            for m in msgs:
                key = (m.get("user_id"), m.get("conversation_id"))
                grouped[key].append(m)

            # Bulk insert each group
            for (user_id, conv_id), group_msgs in grouped.items():
                try:
                    start_bulk = time.monotonic()
                    self.store.bulk_add_messages(user_id, conv_id, group_msgs)
                    elapsed_bulk = time.monotonic() - start_bulk
                    logger.info(
                        f"Flushed {len(group_msgs)} messages to SQLite for conv={conv_id} (bulk latency={elapsed_bulk:.3f}s)",
                        extra={"conversation_id": conv_id}
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to bulk insert messages for conv={conv_id}: {e}", 
                        exc_info=True
                    )
            elapsed_cycle = time.monotonic() - start_cycle
            logger.debug(f"Outbox flush cycle latency={elapsed_cycle:.3f}s, messages_processed={len(msgs)}")