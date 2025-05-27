# backend/app/crawler/document_processor.py
from pathlib import Path
from typing import Dict, List, Optional
import glob
import os

from ..utils.logger import logger
from ..config import KNOWLEDGE_BASE_DIR

class DocumentProcessor:
    """
    Processes and manages markdown documents in the knowledge base.
    """
    
    def __init__(self):
        logger.info("DocumentProcessor initialized")
    
    def list_documents(self) -> List[Dict]:
        """
        List all documents in the knowledge base.
        
        Returns:
            List of document information
        """
        documents = []
        
        try:
            # Ensure the directory exists
            os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
            
            # Find all markdown files
            for file_path in glob.glob(os.path.join(KNOWLEDGE_BASE_DIR, "*.md")):
                path = Path(file_path)
                
                # Get document metadata
                stat = path.stat()
                
                # Get first line as title (assuming it's a markdown heading)
                title = path.stem
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('# '):
                            title = first_line[2:]
                except Exception as e:
                    logger.warning(f"Could not read title from {file_path}: {e}")
                
                documents.append({
                    "id": path.stem,
                    "title": title,
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}", exc_info=True)
            return []
    
    def get_document_content(self, doc_id: str) -> Optional[str]:
        """
        Get the content of a document by ID.
        
        Args:
            doc_id: Document ID (filename without extension)
            
        Returns:
            Document content or None if not found
        """
        try:
            file_path = KNOWLEDGE_BASE_DIR / f"{doc_id}.md"
            
            if not file_path.exists():
                logger.warning(f"Document not found: {doc_id}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return content
            
        except Exception as e:
            logger.error(f"Error reading document {doc_id}: {e}", exc_info=True)
            return None
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID (filename without extension)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = KNOWLEDGE_BASE_DIR / f"{doc_id}.md"
            
            if not file_path.exists():
                logger.warning(f"Document not found for deletion: {doc_id}")
                return False
                
            os.remove(file_path)
            logger.info(f"Deleted document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)
            return False