# backend/app/core/context_classifier.py
import re
from typing import Dict, List, Tuple, Optional
from ..utils.logger import logger

class ContextClassifier:
    """
    Determines whether a user query should trigger RAG or basic conversation.
    """
    
    def __init__(self):
        # Common greeting patterns
        self.greeting_patterns = [
            r'^hi\s*$',
            r'^hello\s*$',
            r'^hey\s*$',
            r'^greetings\s*$',
            r'^good\s+(morning|afternoon|evening)\s*$',
        ]
        
        # System command patterns
        self.system_patterns = [
            r'^help\s*$',
            r'^how\s+do\s+I\s+use\s+this\s*$',
            r'^what\s+can\s+you\s+do\s*$',
            r'^add\s+documentation\s*$',
            r'^add\s+docs\s*$',
            r'^crawl\s+',
            r'^https?://',
        ]
        
        # Compilation for better performance
        self.greeting_regex = re.compile('|'.join(self.greeting_patterns), re.IGNORECASE)
        self.system_regex = re.compile('|'.join(self.system_patterns), re.IGNORECASE)
        
        logger.info("ContextClassifier initialized")
    
    def classify(self, message: str, conversation_history: List[Dict] = None) -> Tuple[str, Optional[str]]:
        """
        Classifies the message to determine appropriate handling.
        
        Args:
            message: User message
            conversation_history: Previous conversation messages
            
        Returns:
            (mode, action) tuple:
              - mode: "direct", "rag", or "system"
              - action: Optional specific action for system commands
        """
        # Clean message for better matching
        clean_message = message.strip().lower()
        
        # Check if this is a greeting
        if self.greeting_regex.match(clean_message):
            logger.info("Classified as greeting/direct response")
            return "direct", None
            
        # Check if this is a system command
        if self.system_regex.match(clean_message):
            # Determine the specific system action
            if re.match(r'^(add\s+docs|add\s+documentation|crawl\s+)', clean_message):
                logger.info("Classified as system command: add_documentation")
                return "system", "add_documentation"
                
            elif re.match(r'^https?://', clean_message):
                logger.info("Classified as system command: crawl_url")
                return "system", "crawl_url"
                
            else:
                logger.info("Classified as system command: help")
                return "system", "help"
        
        # Default to RAG for content-specific queries
        logger.info("Classified as RAG query")
        return "rag", None