# backend/app/utils/file_handler.py
from pathlib import Path
from typing import Dict, List, Optional, Union
import os
import json
import shutil

from .logger import logger
from ..config import KNOWLEDGE_BASE_DIR, VECTOR_STORE_DIR

def load_markdown_files() -> Dict[str, str]:
    """
    Load all markdown files from the knowledge base directory.
    
    Returns:
        Dictionary mapping filename to content
    """
    docs = {}
    
    try:
        # Ensure directory exists
        os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
        
        # Find all markdown files
        for file_path in Path(KNOWLEDGE_BASE_DIR).glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                docs[file_path.stem] = content
                logger.info(f"Loaded markdown file: {file_path.name} ({len(content)} chars)")
            except Exception as e:
                logger.error(f"Error loading markdown file {file_path}: {e}", exc_info=True)
        
        logger.info(f"Loaded {len(docs)} markdown files from {KNOWLEDGE_BASE_DIR}")
        return docs
    except Exception as e:
        logger.error(f"Error loading markdown files: {e}", exc_info=True)
        return {}

def save_markdown_file(filename: str, content: str) -> str:
    """
    Save content as a markdown file in the knowledge base.
    
    Args:
        filename: Filename (without extension)
        content: Markdown content
        
    Returns:
        Full path to the saved file
    """
    try:
        # Ensure directory exists
        os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
        
        # Clean filename
        clean_filename = "".join(c if c.isalnum() or c == "_" else "_" for c in filename)
        
        # Add .md extension if not present
        if not clean_filename.endswith(".md"):
            clean_filename += ".md"
        
        # Full file path
        file_path = Path(KNOWLEDGE_BASE_DIR) / clean_filename
        
        # Write content to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Saved markdown file: {clean_filename} ({len(content)} chars)")
        
        return str(file_path)
    except Exception as e:
        logger.error(f"Error saving markdown file {filename}: {e}", exc_info=True)
        raise

def save_vectorstore(vectorstore, directory: str = None) -> bool:
    """
    Save a vector store to disk.
    
    Args:
        vectorstore: Vector store to save
        directory: Directory to save to (defaults to VECTOR_STORE_DIR)
        
    Returns:
        True if successful, False otherwise
    """
    if directory is None:
        directory = VECTOR_STORE_DIR
    
    try:
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Save vector store
        vectorstore.save_local(directory)
        
        logger.info(f"Saved vector store to {directory}")
        return True
    except Exception as e:
        logger.error(f"Error saving vector store: {e}", exc_info=True)
        return False

def load_vectorstore(directory: str, embeddings) -> Optional[object]:
    """
    Load a vector store from disk.
    
    Args:
        directory: Directory to load from
        embeddings: Embeddings instance
        
    Returns:
        Vector store instance or None if not found
    """
    try:
        if not os.path.exists(directory):
            logger.info(f"Vector store directory {directory} does not exist")
            return None
        
        # Check for required files
        index_path = Path(directory) / "index.faiss"
        docstore_path = Path(directory) / "docstore.pkl"
        
        if not index_path.exists() or not docstore_path.exists():
            logger.info(f"Vector store files not found in {directory}")
            return None
        
        # Load vector store
        from langchain_community.vectorstores import FAISS
        vectorstore = FAISS.load_local(directory, embeddings)
        
        logger.info(f"Loaded vector store from {directory}")
        return vectorstore
    except Exception as e:
        logger.error(f"Error loading vector store: {e}", exc_info=True)
        return None

def backup_knowledge_base(backup_dir: str = None) -> bool:
    """
    Create a backup of the knowledge base.
    
    Args:
        backup_dir: Directory to save the backup (defaults to KNOWLEDGE_BASE_DIR + "_backup")
        
    Returns:
        True if successful, False otherwise
    """
    if backup_dir is None:
        timestamp = Path(__file__).stem
        backup_dir = str(Path(KNOWLEDGE_BASE_DIR).parent / f"knowledge_base_backup_{timestamp}")
    
    try:
        # Ensure source directory exists
        if not os.path.exists(KNOWLEDGE_BASE_DIR):
            logger.warning(f"Knowledge base directory {KNOWLEDGE_BASE_DIR} does not exist")
            return False
        
        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy all files
        file_count = 0
        for file_path in Path(KNOWLEDGE_BASE_DIR).glob("*.md"):
            dest_path = Path(backup_dir) / file_path.name
            shutil.copy2(file_path, dest_path)
            file_count += 1
        
        logger.info(f"Backed up {file_count} files to {backup_dir}")
        return True
    except Exception as e:
        logger.error(f"Error backing up knowledge base: {e}", exc_info=True)
        return False

def list_files(directory: str = None) -> List[Dict]:
    """
    List files in a directory with metadata.
    
    Args:
        directory: Directory to list files from (defaults to KNOWLEDGE_BASE_DIR)
        
    Returns:
        List of dictionaries with file metadata
    """
    if directory is None:
        directory = KNOWLEDGE_BASE_DIR
    
    files = []
    
    try:
        # Ensure directory exists
        if not os.path.exists(directory):
            logger.warning(f"Directory {directory} does not exist")
            return []
        
        # List all files
        for file_path in Path(directory).glob("*.*"):
            # Get file stats
            stats = file_path.stat()
            
            files.append({
                "name": file_path.name,
                "path": str(file_path),
                "size": stats.st_size,
                "modified": stats.st_mtime,
                "extension": file_path.suffix
            })
        
        return files
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {e}", exc_info=True)
        return []