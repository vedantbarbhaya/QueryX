# backend/app/core/chat_handler.py
import json
import re
import textwrap
from typing import Dict, List, Optional, Any
from collections import Counter
from urllib.parse import urlparse
from ..prompts import DIRECT_SYSTEM_PROMPT, RAG_SYSTEM_PROMPT

from ..utils.logger import logger
from ..config import settings, KNOWLEDGE_BASE_DIR
from .conversation_handler import ConversationHandler
from .context_classifier import ContextClassifier
from ..crawler.crawler import DocumentCrawler
from ..crawler.document_processor import DocumentProcessor
from ..rag.vector_store import VectorStoreManager
from .redis_client import increment_question

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

import anyio

def format_docs(docs: List[Document]) -> str:
    """Helper function to format retrieved documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)

def log_and_format_docs(docs: List[Document]) -> str:
    """Logs retrieved documents and formats them."""
    logger.info(f"Retrieved {len(docs)} documents for RAG query")
    for idx, doc in enumerate(docs, start=1):
         preview = doc.page_content[:200].replace("\n", " ")
         source = doc.metadata.get("source", "unknown")
         logger.info(
            f"Doc #{idx} source: {source}, preview: {preview}...",
            extra={"source": source}
         )
    return format_docs(docs)


class ChatHandler:
    """
    Enhanced ChatHandler that:
    - Uses context classification to determine response strategy
    - Supports document crawling and RAG using Langchain Expression Language (LCEL)
    - Provides conversational experience
    """

    def __init__(self):
        logger.info("Initializing ChatHandler")

        # Initialize components
        self.classifier = ContextClassifier()
        self.conversation_handler = ConversationHandler(
            openai_api_key=settings.OPENAI_API_KEY,
            max_messages_without_summary=10,
            model_name=settings.CHAT_MODEL
        )
        self.document_crawler = DocumentCrawler()
        self.document_processor = DocumentProcessor()
        self.vector_store_manager = VectorStoreManager()

        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=settings.CHAT_MODEL,
            temperature=settings.TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Create direct conversation chain using LCEL
        self.direct_chain = self._create_direct_chain()

        # Create RAG chain using LCEL
        self.rag_chain = self._create_rag_chain()

        logger.info("ChatHandler initialized successfully")

    async def get_response(self, message: str, conversation_id: str, user_id: Optional[str] = None) -> Dict:
        """
        Classify the incoming message and delegate to the appropriate handler.
        """
        # Classify message to determine handling mode
        conversation_history = self.conversation_handler.get_messages(conversation_id)
        mode, action = self.classifier.classify(message, conversation_history)
        logger.info(f"Message classified as mode={mode}, action={action}")

        if mode == "direct":
            return await self.handle_direct_query(message, conversation_id, user_id)
        elif mode == "system":
            return await self.handle_system_command(message, action, conversation_id, user_id)
        elif mode == "rag":
            return await self.handle_rag_query(message, conversation_id, user_id)
        else:
            # Fallback to direct conversation
            logger.warning(f"Unknown mode '{mode}', falling back to direct query.")
            return await self.handle_direct_query(message, conversation_id, user_id)

    def _create_direct_chain(self):
        """Create a direct conversation chain without RAG using LCEL"""
        # Incorporates conversation history using MessagesPlaceholder
        prompt = ChatPromptTemplate.from_messages([
            ("system", DIRECT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{question}")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain

    def _create_rag_chain(self) -> Any:
        """
        Create a RAG chain using LCEL, incorporating context retrieval,
        logging, formatting, prompting, and LLM execution.

        Returns:
            A runnable RAG chain.
        """
        retriever = self.vector_store_manager.get_retriever()

        # Define the prompt template for RAG
        # Assumes RAG_SYSTEM_PROMPT provides general instructions.
        # Context and Question are explicitly inserted.
        rag_prompt_template = ChatPromptTemplate.from_messages([
            ("system", RAG_SYSTEM_PROMPT + """
            Context:
            {context}"""),
            MessagesPlaceholder(variable_name="chat_history"), # Include history for conversational RAG
            ("user", "{question}")
        ])

        # Construct the RAG chain using LCEL pipe operator
        rag_chain = (
            {
                # Explicitly extract "context" from input before passing to retriever and formatter
                "context": RunnableLambda(lambda inp: inp["context"]) | retriever | RunnableLambda(log_and_format_docs),
                # Pass the original question through
                "question": RunnableLambda(lambda inp: inp["question"]),
                # Extract the chat history list directly
                "chat_history": RunnableLambda(lambda inp: inp["chat_history"]),
            }
            | rag_prompt_template   # Populate the prompt template
            | self.llm              # Invoke the language model
            | StrOutputParser()     # Parse the output as a string
        )
        return rag_chain

    async def handle_direct_query(self, message: str, conversation_id: str, user_id: Optional[str] = None) -> Dict:
        """Handle a direct conversation query without RAG using LCEL"""

        # Add user message to conversation
        await self.conversation_handler.add_message(
            user_id,
            conversation_id=conversation_id,
            role="user",
            content=message
        )

        # Get conversation history for the chain
        chat_history = await self.conversation_handler.get_messages_for_llm(user_id, conversation_id)

        # Invoke the direct chain with the current question and history
        response = await self.direct_chain.ainvoke({
            "question": message,
            "chat_history": chat_history
        })

        # Add response to conversation
        await self.conversation_handler.add_message(
            user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=response
        )

        return {
            "response": response,
            "conversation_id": conversation_id
        }

    async def handle_rag_query(self, message: str, conversation_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a RAG-based query using the LCEL chain: retrieve documents (implicitly),
        log them (via RunnableLambda), generate a response, and update conversation.

        Args:
            message: The user query string.
            conversation_id: The ID of the conversation.

        Returns:
            A dict with keys "response" and "conversation_id".
        """
        # Log entry into the method
        logger.info(f"handle_rag_query called with conversation_id={conversation_id}, message={message}")

        # 1. Add user message to conversation
        await self.conversation_handler.add_message(
            user_id,
            conversation_id=conversation_id,
            role="user",
            content=message
        )

        # 2. Ensure documentation is loaded
        if not self.vector_store_manager.has_documents():
            no_docs_msg = (
                "I don't have any API documentation loaded yet. "
                "Please paste a URL to the API docs you'd like me to use, or tell me to 'add documentation'."
            )
            self.conversation_handler.add_message(
                user_id,
                conversation_id=conversation_id,
                role="assistant",
                content=no_docs_msg
            )
            return {"response": no_docs_msg, "conversation_id": conversation_id}

        # 3. Retrieve source documents for metadata
        retriever = self.vector_store_manager.get_retriever()
        try:
            docs = retriever.get_relevant_documents(message)
        except Exception:
            docs = []
        source_ids = [doc.metadata.get("source") or doc.metadata.get("id") for doc in docs]
        logger.debug(f"Source document IDs for conversation_id={conversation_id}: {source_ids}")

        # 4. Get conversation history for the RAG chain
        chat_history = await self.conversation_handler.get_messages_for_llm(user_id, conversation_id)
        logger.debug(f"RAG chat_history length={len(chat_history)} for conversation_id={conversation_id}")

        # Convert chat_history dicts to BaseMessage objects
        base_history = []
        for msg in chat_history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                base_history.append(HumanMessage(content=content))
            elif role == "assistant":
                base_history.append(AIMessage(content=content))
            else:
                base_history.append(SystemMessage(content=content))
        logger.debug(f"Converted chat_history to {len(base_history)} BaseMessage objects")

        # 5. Invoke the RAG chain
        logger.debug(f"Invoking RAG chain with context and question; chat_history length={len(base_history)}")
        try:
            response = await self.rag_chain.ainvoke({
                "context": message,
                "question": message,
                "chat_history": base_history
            })
            logger.info(f"RAG chain returned response for conversation_id={conversation_id}: {response}")
        except Exception as e:
            logger.error(f"Error invoking RAG chain for conversation {conversation_id}: {str(e)}", exc_info=True)
            response = "I encountered an error trying to find information in the documentation. Please try rephrasing your question or check the logs."

        # Determine API ID for Top-K: explicit metadata or fallback detect
        meta = self.conversation_handler.get_metadata(conversation_id) or {}
        api_id = meta.get("api_id")
        if not api_id:
            detected = self.conversation_handler.detect_api_id(message)
            api_id = detected or conversation_id
        try:
            increment_question(api_id, message)
        except Exception as e:
            logger.warning(f"Failed to increment Top-K question counter for api_id={api_id}: {e}", exc_info=True)

        # 6. Add assistant response to conversation
        await self.conversation_handler.add_message(
            user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=response, # The chain directly returns the string response
            metadata={"source_docs": source_ids}
        )

        # 7. Log the updated conversation summary (optional, but good practice)
        summary_info = self.conversation_handler.get_conversation_summary(conversation_id)
        if summary_info: # It might return None if no summary exists yet
            logger.info(
                f"Conversation summary updated for {conversation_id}",
                extra={"summary_details": summary_info}
            )
            summary_text = summary_info.get("summary") if isinstance(summary_info, dict) else str(summary_info)
            logger.debug(f"Summary text for {conversation_id}: {summary_text}")

        # 8. Return the response
        return {
            "response": response,
            "conversation_id": conversation_id
        }

    async def handle_welcome_message(self, conversation_id: str) -> Dict:
        """Handle the welcome message for a new conversation"""
        welcome_message = textwrap.dedent("""
            👋 Welcome to the API Documentation Assistant!

            I can help you explore and understand API documentation. Here's what I can do:

            1️⃣ **Add Documentation**: Provide a URL to API documentation you want to explore
            2️⃣ **Answer Questions**: Ask questions about the loaded documentation
            3️⃣ **Explain Concepts**: Get explanations of API concepts

            To get started, please provide a URL to the API documentation you'd like to explore, or ask a question about previously loaded documentation.
        """).strip()

        # Add to conversation
        await self.conversation_handler.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=welcome_message
        )

        return {
            "response": welcome_message,
            "conversation_id": conversation_id
        }

    async def handle_system_command(self, message: str, action: str, conversation_id: str, user_id: Optional[str] = None) -> Dict:
        """Handle system commands like crawling or help"""

        # Add user message to conversation
        await self.conversation_handler.add_message(
            user_id,
            conversation_id=conversation_id,
            role="user",
            content=message
        )

        response = ""

        if action == "help":
            response = textwrap.dedent("""
            📚 **API Documentation Assistant Help**

            I can:
            - Crawl API documentation from a URL (just paste the URL)
            - Answer questions about API documentation
            - Explain API concepts and usage

            Commands:
            - `add documentation` or paste a URL: Add new API documentation
            - `list documents`: Show all loaded documentation (Not Implemented)
            - `help`: Show this help message

            To get started, paste a URL to API documentation you want to explore.
            """).strip() # Added placeholder for list documents

        elif action == "add_documentation":
            response = textwrap.dedent("""
            Please provide the URL to the API documentation you want to add.

            For example: https://api.example.com/docs
            """).strip()

        elif action == "crawl_url":
            # Extract URL from the message
            url_match = re.search(r'(https?://\S+)', message)
            if url_match:
                url = url_match.group(1).rstrip('.,;!?') # Clean trailing punctuation
                logger.info(f"Attempting to crawl URL: {url}")

                # Show thinking message - Add to conversation *before* long operation
                thinking_response = f"Processing URL: {url}. I'll start crawling and indexing the documentation. This may take a few moments..."
                await self.conversation_handler.add_message(
                    user_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=thinking_response
                )
                # NOTE: Ideally, send this thinking message back to the user interface immediately

                try:
                    # Perform the crawl
                    result = await self.document_crawler.crawl_url(url)

                    if result["success"]:
                        # Refresh vector store with new document(s)
                        # This might involve reprocessing depending on DocumentProcessor setup
                        logger.info(f"Crawling successful for {url}. Refreshing vector store.")
                        self.vector_store_manager.refresh_vector_store() # Assume this loads new docs

                        # Build success message
                        response = textwrap.dedent(f"""
                        ✅ Successfully processed and indexed documentation from {url}

                        📊 Statistics (from crawl):
                        - Words: {result.get("word_count", "N/A")}
                        - Links Found: {result.get("link_count", "N/A")}
                        - Files Saved: {len(result.get("saved_files", []))}

                        You can now ask questions about this API documentation!
                        """).strip()
                        # Register this API for fallback detection
                        api_id = conversation_id
                        self.conversation_handler.set_metadata(conversation_id, "api_id", api_id)
                        parsed = urlparse(url)
                        path_tokens = [seg for seg in parsed.path.split("/") if seg]
                        keywords = [parsed.netloc] + path_tokens
                        self.conversation_handler.register_api(api_id, keywords)
                    else:
                        response = textwrap.dedent(f"""
                        ❌ Failed to crawl documentation from {url}

                        Reason: {result.get("error", "Unknown error during crawling")}

                        Please check the URL and ensure the site is accessible.
                        """).strip()
                except Exception as e:
                    logger.error(f"Error during crawl_url handling for {url}: {str(e)}", exc_info=True)
                    response = textwrap.dedent(f"""
                    ❌ An unexpected error occurred while processing the URL: {url}

                    Error details: {str(e)}

                    Please try a different URL or check the application logs.
                    """).strip()
            else:
                response = "I couldn't find a valid URL (starting with http:// or https://) in your message. Please provide the full URL."

        # Add final response to conversation
        await self.conversation_handler.add_message(
            user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=response
        )

        return {
            "response": response, # Return the final status message
            "conversation_id": conversation_id
        }

