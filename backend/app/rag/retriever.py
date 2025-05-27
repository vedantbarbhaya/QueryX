# backend/app/rag/retriever.py
import os
from typing import List, Dict, Any, Optional

from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.retrievers import ContextualCompressionRetriever
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.retrievers.multi_query import MultiQueryRetriever

from ..utils.logger import logger
from ..config import settings, KNOWLEDGE_BASE_DIR, VECTOR_STORE_DIR

class EnhancedRetriever:
    """
    Enhanced document retriever with additional features:
    - Multi-query retrieval
    - Contextual compression
    - Relevance filtering
    """
    
    def __init__(self, base_retriever):
        """
        Initialize the enhanced retriever with a base retriever.
        
        Args:
            base_retriever: Base retriever from the vector store
        """
        self.base_retriever = base_retriever
        
        # Initialize LLM for enhanced retrieval
        self.llm = ChatOpenAI(
            model_name=settings.CHAT_MODEL,
            temperature=0.1,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Initialize compressor for contextual compression
        self.compressor = LLMChainExtractor.from_llm(self.llm)
        
        # Initialize the contextual compression retriever
        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=self.base_retriever
        )
        
        # Initialize multi-query retriever
        self.multi_query_retriever = MultiQueryRetriever.from_llm(
            retriever=self.base_retriever,
            llm=self.llm
        )
        
        logger.info("EnhancedRetriever initialized")
    
    async def aretrieve_with_compression(self, query: str) -> List[Document]:
        """
        Retrieve documents with contextual compression.
        
        Args:
            query: Query string
            
        Returns:
            List of compressed documents
        """
        try:
            logger.info(f"Retrieving with compression for query: {query[:50]}...")
            compressed_docs = await self.compression_retriever.aget_relevant_documents(query)
            logger.info(f"Retrieved {len(compressed_docs)} compressed documents")
            return compressed_docs
        except Exception as e:
            logger.error(f"Error retrieving with compression: {e}", exc_info=True)
            # Fall back to base retriever
            logger.info("Falling back to base retriever")
            return await self.base_retriever.aget_relevant_documents(query)
    
    async def aretrieve_with_multi_query(self, query: str) -> List[Document]:
        """
        Retrieve documents using multiple query variations.
        
        Args:
            query: Original query string
            
        Returns:
            List of documents from multiple queries
        """
        try:
            logger.info(f"Retrieving with multi-query for query: {query[:50]}...")
            multi_query_docs = await self.multi_query_retriever.aget_relevant_documents(query)
            logger.info(f"Retrieved {len(multi_query_docs)} documents with multi-query")
            return multi_query_docs
        except Exception as e:
            logger.error(f"Error retrieving with multi-query: {e}", exc_info=True)
            # Fall back to base retriever
            logger.info("Falling back to base retriever")
            return await self.base_retriever.aget_relevant_documents(query)
    
    async def aretrieve_with_hybrid(self, query: str) -> List[Document]:
        """
        Perform a hybrid retrieval using multiple methods and deduplicating results.
        
        Args:
            query: Query string
            
        Returns:
            List of unique documents
        """
        try:
            logger.info(f"Performing hybrid retrieval for query: {query[:50]}...")
            
            # Get documents from base retriever
            base_docs = await self.base_retriever.aget_relevant_documents(query)
            logger.info(f"Retrieved {len(base_docs)} documents from base retriever")
            
            # Get documents from compression retriever
            compressed_docs = await self.compression_retriever.aget_relevant_documents(query)
            logger.info(f"Retrieved {len(compressed_docs)} documents from compression retriever")
            
            # Combine and deduplicate documents
            all_docs = base_docs + compressed_docs
            unique_docs = self._deduplicate_documents(all_docs)
            logger.info(f"Combined and deduplicated to {len(unique_docs)} documents")
            
            return unique_docs
            
        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}", exc_info=True)
            # Fall back to base retriever
            logger.info("Falling back to base retriever")
            return await self.base_retriever.aget_relevant_documents(query)
    
    def _deduplicate_documents(self, documents: List[Document]) -> List[Document]:
        """
        Deduplicate documents by content.
        
        Args:
            documents: List of documents
            
        Returns:
            Deduplicated list of documents
        """
        unique_contents = set()
        unique_docs = []
        
        for doc in documents:
            content = doc.page_content
            if content not in unique_contents:
                unique_contents.add(content)
                unique_docs.append(doc)
        
        return unique_docs
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the retriever.
        
        Returns:
            Dictionary with retriever statistics
        """
        # This is a placeholder - actual implementation would depend on
        # the specific base retriever you're using
        return {
            "retriever_type": type(self.base_retriever).__name__,
            "has_compressor": bool(self.compressor),
            "has_multi_query": bool(self.multi_query_retriever)
        }