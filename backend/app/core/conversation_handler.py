# backend/app/core/conversation_handler.py
from typing import Any, Dict, List, Optional, Set
import time
from datetime import datetime
from langchain_openai import ChatOpenAI
from ..utils.logger import logger
from .conversation_store import SQLiteConversationStore

# RabbitMQ publisher for chat messages
from .message_queue import publish_chat_message
from .redis_client import cache_chat_message, get_cached_messages

class ConversationHandler:
    """
    Manages conversation state and context for chat-based interactions.
    - Stores conversation messages
    - Summarizes older messages when a threshold is exceeded
    - Provides history/context for LLM
    """
    def __init__(
        self,
        openai_api_key: str,
        max_messages_without_summary: int = 10,
        model_name: str = "gpt-4o-mini"
    ):
        self.openai_api_key = openai_api_key
        self.max_messages_without_summary = max_messages_without_summary
        self.model_name = model_name
        self.summarization_model = ChatOpenAI(
            model_name=model_name,
            temperature=0.3,
            openai_api_key=openai_api_key
        )
        # conversation_id -> { "messages": [...], "summary": str, "metadata": {}, ... }
        self.conversations: Dict[str, Dict] = {}
        self.store = SQLiteConversationStore("conversations.db")

        # Registry of loaded APIs → keywords for fallback detection
        self.api_registry: Dict[str, Set[str]] = {}

        logger.info("ConversationHandler initialized")

    async def add_message(
        self,
        user_id,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "messages": [],
                "summary": "",
                "metadata": {},
                "last_active": time.time(),
                "created_at": time.time()
            }
            logger.info(f"Created new conversation: {conversation_id}")
        conv_data = self.conversations[conversation_id]
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        if metadata:
            message["metadata"] = metadata
        conv_data["messages"].append(message)
        conv_data["last_active"] = time.time()
        logger.info(f"Added {role} message to conversation {conversation_id[:8]}: {content[:50]}...")
        # Publish to RabbitMQ outbox for durable logging
        try:
            await publish_chat_message(
                user_id,
                conversation_id,
                role,
                content,
                metadata
            )
        except Exception as e:
            logger.error(f"Failed to publish message to RabbitMQ: {e}", exc_info=True)
        # persisting the history
        #self.store.add_message(user_id, conversation_id, role, content, metadata)

        # also cache it hot in Redis
        try:
            await cache_chat_message(user_id, conversation_id, role, content)
        except Exception:
            logger.warning("Redis cache_chat_message failed", exc_info=True)
        if len(conv_data["messages"]) > self.max_messages_without_summary:
            logger.info(f"Message count ({len(conv_data['messages'])}) exceeded threshold for conversation {conversation_id[:8]}. Summarizing...")
            self._summarize_and_trim(conversation_id)

    def get_messages(
        self,
        conversation_id: str
    ) -> List[Dict]:
        if conversation_id not in self.conversations:
            return []
        return self.conversations[conversation_id].get("messages", [])

    async def get_messages_for_llm(self, user_id, conversation_id: str) -> List[Dict]:
        logger.debug(f"get_messages_for_llm called for conversation_id={conversation_id}")

        # 1. Try Redis hot‐cache
        try:
            cached = await get_cached_messages(user_id, conversation_id)
        except Exception:
            logger.warning("Redis get_cached_messages failed", exc_info=True)
            cached = []

        if cached:
            logger.debug(f"Returning {len(cached)} cached messages for {conversation_id}")
            return [{"role": m["role"], "content": m["content"]} for m in cached]

        # 2. Cache miss → load from SQLite
        try:
            rows = self.store.get_messages(user_id, conversation_id)
        except Exception:
            logger.error("SQLite get_messages failed", exc_info=True)
            return []

        # 3. Warm the cache
        for msg in rows:
            try:
                await cache_chat_message(
                    user_id,
                    conversation_id,
                    msg["role"],
                    msg["content"],
                    timestamp=msg.get("timestamp")
                )
            except Exception:
                logger.warning("Redis cache_chat_message warm failed", exc_info=True)

        result = [{"role": m["role"], "content": m["content"]} for m in rows]
        logger.debug(f"Returning {len(result)} SQLite messages for {conversation_id}")
        return result

    def get_conversation_summary(
        self,
        conversation_id: str
    ) -> Optional[Dict]:
        """
        Returns a summary object for the conversation, or None if it doesn't exist.
        """
        if conversation_id not in self.conversations:
            return None
        conv_data = self.conversations[conversation_id]
        messages = conv_data.get("messages", [])
        # Use first user message as title if available
        first_user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
        title = (first_user_message[:50] + "...") if len(first_user_message) > 50 else first_user_message
        created_at = conv_data.get("created_at", 0)
        last_active = conv_data.get("last_active", 0)
        return {
            "id": conversation_id,
            "title": title or "New Conversation",
            "message_count": len(messages),
            "summary": conv_data.get("summary", ""),
            "created_at": created_at,
            "last_active": last_active,
            "created_at_readable": datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S') if created_at else "",
            "last_active_readable": datetime.fromtimestamp(last_active).strftime('%Y-%m-%d %H:%M:%S') if last_active else "",
            "exists": True,
            "metadata": conv_data.get("metadata", {})
        }

    def _summarize_and_trim(
        self,
        conversation_id: str
    ) -> None:
        conv_data = self.conversations[conversation_id]
        all_messages = conv_data["messages"]
        keep_in_full_count = min(self.max_messages_without_summary // 2, 5)
        if len(all_messages) <= keep_in_full_count:
            return
        to_summarize = all_messages[:-keep_in_full_count]
        to_keep = all_messages[-keep_in_full_count:]
        logger.info(f"Summarizing {len(to_summarize)} messages for conversation {conversation_id[:8]}. Keeping the last {keep_in_full_count} messages in full.")
        summary_chunk = self._summarize_messages(to_summarize)
        existing_summary = conv_data.get("summary", "")
        if existing_summary:
            conv_data["summary"] = f"{existing_summary}\n\n{summary_chunk}"
        else:
            conv_data["summary"] = summary_chunk
        conv_data["messages"] = to_keep

    def _summarize_messages(
        self,
        messages: List[Dict]
    ) -> str:
        if not messages:
            return ""
        try:
            conversation_text = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}" for msg in messages
            )
            prompt = (
                "Please summarize the following conversation snippets concisely, focusing on key points, "
                "questions asked, information provided, and any decisions made. The summary should be "
                "about 2-3 paragraphs and maintain the important context needed for the conversation to continue.\n\n"
                f"CONVERSATION TO SUMMARIZE:\n{conversation_text}\n\nSUMMARY:"
            )
            messages_for_model = [
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely while retaining important context."},
                {"role": "user", "content": prompt}
            ]
            response = self.summarization_model.invoke(messages_for_model)
            summary = response.content
            logger.debug(f"Generated summary ({len(summary)} chars)")
            return summary
        except Exception as e:
            logger.error(f"Error summarizing messages: {e}", exc_info=True)
            return "(Summary unavailable due to an error)"
    def set_metadata(self, conversation_id: str, key: str, value: Any) -> None:
        """Set arbitrary metadata for a conversation."""
        conv = self.conversations.setdefault(conversation_id, {
            "messages": [], "summary": "", "metadata": {},
            "last_active": time.time(), "created_at": time.time()
        })
        conv["metadata"][key] = value

    def get_metadata(self, conversation_id: str) -> Dict[str, Any]:
        """Get metadata dict for a conversation (or empty)."""
        return self.conversations.get(conversation_id, {}).get("metadata", {})

    def register_api(self, api_id: str, keywords: List[str]) -> None:
        """
        Register an API identifier with associated keywords for fallback detection.
        """
        self.api_registry[api_id] = {kw.lower() for kw in keywords if kw}

    def detect_api_id(self, question: str) -> Optional[str]:
        """
        Fallback: scan the question text for any registered keyword.
        Returns the first matching api_id, or None if no match.
        """
        q = question.lower()
        for api_id, keywords in self.api_registry.items():
            for kw in keywords:
                if kw in q:
                    return api_id
        return None