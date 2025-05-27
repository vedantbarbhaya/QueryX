# backend/app/rag/vector_store.py
import os
import faiss
from typing import Dict, List, Optional
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import MarkdownTextSplitter
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from ..config import settings, KNOWLEDGE_BASE_DIR, VECTOR_STORE_DIR
from ..utils.logger import logger

class VectorStoreManager:
    """
    Manages the vector store for RAG functionality.
    """
    
    def __init__(self):
        logger.info("Initializing VectorStoreManager")
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Initialize vector store
        self.vector_store = self._initialize_vector_store()
        
        logger.info("VectorStoreManager initialized")
    
    def _initialize_vector_store(self) -> FAISS:
        """Initialize or load the FAISS vector store"""
        try:
            # Check if vector store exists
            if self._vector_store_exists():
                logger.info("Loading existing vector store")
                vector_store = self._load_vector_store()
                if vector_store:
                    return vector_store
            
            # Create a new vector store
            logger.info("Creating new vector store")
            return self._create_vector_store()
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}", exc_info=True)
            # Create an empty vector store as fallback
            return self._create_empty_vector_store()
    
    def _vector_store_exists(self) -> bool:
        """Check if vector store exists on disk"""
        index_path = Path(VECTOR_STORE_DIR) / "index.faiss"
        docstore_path = Path(VECTOR_STORE_DIR) / "docstore.pkl"
        return index_path.exists() and docstore_path.exists()
    
    def _load_vector_store(self) -> Optional[FAISS]:
        """Load vector store from disk"""
        try:
            os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
            vector_store = FAISS.load_local(VECTOR_STORE_DIR, self.embeddings)
            return vector_store
        except Exception as e:
            logger.error(f"Error loading vector store: {e}", exc_info=True)
            return None
    
    def _create_empty_vector_store(self) -> FAISS:
        """Create an empty vector store"""
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        
        # Create a sample embedding to initialize dimensions
        sample_embedding = self.embeddings.embed_query("test")
        index = faiss.IndexFlatL2(len(sample_embedding))
        
        # Create the empty vector store
        vector_store = FAISS(
            embedding_function=self.embeddings,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={}
        )
        
        # Save the empty vector store
        vector_store.save_local(VECTOR_STORE_DIR)
        
        return vector_store
    
    def _create_vector_store(self) -> FAISS:
        """Create a new vector store from documents"""
        # Start with an empty vector store
        vector_store = self._create_empty_vector_store()
        
        # Add documents if they exist
        docs = self._load_documents()
        if docs:
            vector_store.add_documents(docs)
            vector_store.save_local(VECTOR_STORE_DIR)
            logger.info(f"Created vector store with {len(docs)} documents")
        
        return vector_store
    
    def _load_documents(self) -> List[Document]:
        """Load documents from the knowledge base"""
        documents = []
        
        try:
            if not os.path.exists(KNOWLEDGE_BASE_DIR):
                logger.info("Knowledge base directory doesn't exist")
                return []
            
            # Load all markdown files
            md_files = list(Path(KNOWLEDGE_BASE_DIR).glob("*.md"))
            logger.info(f"Found {len(md_files)} markdown files")
            
            # Create text splitter
            text_splitter = MarkdownTextSplitter(
                chunk_size=settings.VECTOR_STORE_CHUNK_SIZE,
                chunk_overlap=settings.VECTOR_STORE_CHUNK_OVERLAP
            )
            
            # Process each file
            for file_path in md_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Split text into chunks
                    chunks = text_splitter.split_text(content)
                    logger.info(f"Split {file_path.name} into {len(chunks)} chunks")
                    
                    # Create Document objects
                    doc_chunks = [
                        Document(
                            page_content=chunk,
                            metadata={"source": file_path.stem}
                        )
                        for chunk in chunks
                    ]
                    
                    documents.extend(doc_chunks)
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading documents: {e}", exc_info=True)
            return []
    
    def refresh_vector_store(self) -> bool:
        """Refresh the vector store with latest documents"""
        try:
            logger.info("Refreshing vector store")
            self.vector_store = self._create_vector_store()
            return True
        except Exception as e:
            logger.error(f"Error refreshing vector store: {e}", exc_info=True)
            return False
    
    def get_retriever(self):
        """Get the retriever for RAG"""
        # Use the raw retriever for compatibility with RetrievalQA
        return self.vector_store.as_retriever(
            search_kwargs={"k": settings.K_RETRIEVAL}
        )
    
    def has_documents(self) -> bool:
        """Check if the vector store has any documents"""
        try:
        # If the FAISS index reports zero vectors, bail out early
            if getattr(self.vector_store.index, 'ntotal', 0) == 0:
                return False
            docs = self.vector_store.similarity_search("test", k=1)
            return len(docs) > 0
        except Exception as e:
            logger.error(f"Error checking if vector store has documents: {e}")
            return False
            
    def get_document_count(self) -> int:
        """Get the number of documents in the vector store"""
        try:
            # This is an approximation - FAISS doesn't provide a direct way to count documents
            return len(self.vector_store.docstore._dict)
        except Exception as e:
            logger.error(f"Error getting document count: {e}", exc_info=True)
            return 0
            
    def clear_vector_store(self) -> bool:
        """Clear all documents from the vector store"""
        try:
            logger.info("Clearing vector store")
            self.vector_store = self._create_empty_vector_store()
            return True
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}", exc_info=True)
            return False
            
    def get_document_sources(self) -> List[str]:
        """Get a list of unique document sources in the vector store"""
        try:
            sources = set()
            for doc_id, doc in self.vector_store.docstore._dict.items():
                if hasattr(doc, 'metadata') and 'source' in doc.metadata:
                    sources.add(doc.metadata['source'])
            return list(sources)
        except Exception as e:
            logger.error(f"Error getting document sources: {e}", exc_info=True)
            return []