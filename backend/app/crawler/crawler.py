# backend/app/crawler/crawler.py
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from urllib.parse import urlparse

from ..utils.logger import logger
from ..config import KNOWLEDGE_BASE_DIR

class DocumentCrawler:
    """
    Crawls API documentation websites and saves content as markdown files.
    """
    
    def __init__(self):
        self.browser_config = BrowserConfig(verbose=True)
        self.run_config = CrawlerRunConfig(
            # Content filtering
            word_count_threshold=10,
            excluded_tags=['form', 'header', 'footer', 'nav'],
            exclude_external_links=True,

            # Content processing
            process_iframes=True,
            remove_overlay_elements=True,
        )
        logger.info("DocumentCrawler initialized")
    
    async def crawl_url(self, url: str, doc_name: Optional[str] = None) -> Dict:
        """
        Crawl a URL and save the content as markdown.
        
        Args:
            url: The URL to crawl
            doc_name: Optional name for the document
            
        Returns:
            Dict with crawl results
        """
        logger.info(f"Starting crawl for URL: {url}")
        
        try:
            # Parse URL to get domain for default document name
            if not doc_name:
                parsed_url = urlparse(url)
                doc_name = parsed_url.netloc.replace(".", "_")
            
            # Clean document name for file system
            doc_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in doc_name)
            
            # Ensure knowledge base directory exists
            os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
            
            # Perform the crawl
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=self.run_config
                )
                
                if not result.success:
                    logger.error(f"Crawl failed: {result.error_message}")
                    return {
                        "success": False,
                        "error": result.error_message
                    }
                
                # Process and save the content
                output_file = KNOWLEDGE_BASE_DIR / f"{doc_name}.md"
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# {url} Documentation\n\n")
                    # Use the updated MarkdownGenerationResult API
                    f.write(result.markdown.raw_markdown)
                
                # Log link information
                internal_links = [link['href'] for link in result.links.get("internal", [])]
                logger.info(f"Found {len(internal_links)} internal links")

                # Return success result
                return {
                    "success": True,
                    "file_path": str(output_file),
                    "word_count": len(result.markdown.raw_markdown.split()),
                    "link_count": len(internal_links)
                }
                
        except Exception as e:
            logger.error(f"Error during crawl: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def crawl_multiple_urls(self, urls: List[str], base_name: Optional[str] = None) -> Dict:
        """
        Crawl multiple URLs and combine into a single document
        
        Args:
            urls: List of URLs to crawl
            base_name: Optional base name for the combined document
            
        Returns:
            Dict with crawl results
        """
        logger.info(f"Starting crawl for {len(urls)} URLs")
        
        if not base_name:
            # Use the domain of the first URL as the base name
            parsed_url = urlparse(urls[0])
            base_name = parsed_url.netloc.replace(".", "_")
        
        # Clean base name for file system
        base_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in base_name)
        
        results = []
        success_count = 0
        
        for i, url in enumerate(urls):
            result = await self.crawl_url(url, f"{base_name}_part{i+1}")
            results.append(result)
            if result["success"]:
                success_count += 1
        
        return {
            "success": success_count > 0,
            "total_urls": len(urls),
            "successful_crawls": success_count,
            "results": results
        }