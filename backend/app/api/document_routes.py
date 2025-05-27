# backend/app/api/document_routes.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List

from ..crawler.crawler import DocumentCrawler
from ..crawler.document_processor import DocumentProcessor
from ..rag.vector_store import VectorStoreManager
from ..utils.logger import logger

router = APIRouter(prefix="/api/documents", tags=["documents"])

class CrawlRequest(BaseModel):
    url: HttpUrl
    name: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    title: str
    path: str
    size_bytes: int
    modified: float

# Initialize components
document_crawler = DocumentCrawler()
document_processor = DocumentProcessor()
vector_store_manager = VectorStoreManager()

@router.post("/crawl", status_code=202)
async def crawl_url(request: CrawlRequest):
    """
    Crawl a URL and add the content to the knowledge base.
    
    Returns a status and message.
    """
    try:
        logger.info(f"Received crawl request for URL: {request.url}")
        
        # Perform the crawl
        result = await document_crawler.crawl_url(str(request.url), request.name)
        
        if not result["success"]:
            logger.error(f"Crawl failed: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to crawl URL: {result.get('error', 'Unknown error')}"
            )
        
        # Refresh the vector store
        vector_store_manager.refresh_vector_store()
        
        return {
            "status": "success",
            "message": f"Successfully crawled URL and added to knowledge base",
            "details": {
                "file_path": result["file_path"],
                "word_count": result["word_count"],
                "link_count": result.get("link_count", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error crawling URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while crawling the URL: {str(e)}"
        )

@router.get("", response_model=List[DocumentResponse])
async def list_documents():
    """
    List all documents in the knowledge base.
    """
    try:
        documents = document_processor.list_documents()
        return documents
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while listing documents: {str(e)}"
        )

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """
    Get a document by ID.
    """
    try:
        content = document_processor.get_document_content(doc_id)
        
        if content is None:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {doc_id} not found"
            )
        
        return {
            "id": doc_id,
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {doc_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while getting the document: {str(e)}"
        )

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document by ID.
    """
    try:
        success = document_processor.delete_document(doc_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {doc_id} not found or could not be deleted"
            )
        
        # Refresh the vector store
        vector_store_manager.refresh_vector_store()
        
        return {
            "status": "success",
            "message": f"Document {doc_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the document: {str(e)}"
        )

@router.post("/refresh-vector-store")
async def refresh_vector_store():
    """
    Refresh the vector store with the latest documents.
    """
    try:
        success = vector_store_manager.refresh_vector_store()
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to refresh vector store"
            )
        
        return {
            "status": "success",
            "message": "Vector store refreshed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing vector store: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while refreshing the vector store: {str(e)}"
        )