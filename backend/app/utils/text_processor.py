# backend/app/utils/text_processor.py
import re
from typing import Dict, List, Optional
import unicodedata
import html

from .logger import logger

def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Input text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    try:
        # Decode HTML entities
        text = html.unescape(text)
        
        # Normalize Unicode
        text = unicodedata.normalize('NFKC', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip whitespace
        text = text.strip()
        
        return text
    except Exception as e:
        logger.error(f"Error cleaning text: {e}", exc_info=True)
        return text

def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """
    Extract code blocks from markdown.
    
    Args:
        text: Markdown text
        
    Returns:
        List of dictionaries with 'language' and 'code' keys
    """
    if not text:
        return []
    
    try:
        # Find all code blocks
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        code_blocks = []
        for match in matches:
            language = match.group(1).strip() or "text"
            code = match.group(2).strip()
            
            code_blocks.append({
                "language": language,
                "code": code
            })
        
        return code_blocks
    except Exception as e:
        logger.error(f"Error extracting code blocks: {e}", exc_info=True)
        return []

def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Input text
        
    Returns:
        List of URLs
    """
    if not text:
        return []
    
    try:
        # Find all URLs
        url_pattern = r'https?://[^\s)>]+'
        urls = re.findall(url_pattern, text)
        
        return urls
    except Exception as e:
        logger.error(f"Error extracting URLs: {e}", exc_info=True)
        return []

def format_api_response(response: str) -> str:
    """
    Format API responses for better readability.
    
    Args:
        response: Raw response text
        
    Returns:
        Formatted response
    """
    if not response:
        return ""
    
    try:
        # Ensure code blocks are properly formatted
        response = re.sub(
            r'```(\w*)\n(.*?)\n```',
            lambda m: f'```{m.group(1)}\n{m.group(2).strip()}\n```',
            response,
            flags=re.DOTALL
        )
        
        # Format API endpoints consistently
        response = re.sub(
            r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)',
            r'`\1 \2`',
            response
        )
        
        # Ensure proper spacing after bullet points
        response = re.sub(r'(\*|\-|\d+\.)\s*([A-Z])', r'\1 \2', response)
        
        return response
    except Exception as e:
        logger.error(f"Error formatting API response: {e}", exc_info=True)
        return response

def extract_main_content(html_content: str) -> str:
    """
    Extract main content from HTML.
    
    Args:
        html_content: HTML content
        
    Returns:
        Extracted main content as markdown
    """
    try:
        # This is a placeholder - in a real implementation,
        # you would use a library like BeautifulSoup to extract content
        # For now, we'll use a simple regex-based approach
        
        # Remove HTML comments
        content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
        
        # Remove script and style tags
        content = re.sub(r'<script.*?>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style.*?>.*?</style>', '', content, flags=re.DOTALL)
        
        # Remove HTML tags
        content = re.sub(r'<[^>]*>', '', content)
        
        # Decode HTML entities
        content = html.unescape(content)
        
        # Clean whitespace
        content = clean_text(content)
        
        return content
    except Exception as e:
        logger.error(f"Error extracting main content: {e}", exc_info=True)
        return ""