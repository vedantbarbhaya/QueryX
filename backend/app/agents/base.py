from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel

class AgentAction(Enum):
    VALIDATE_API = "validate_api"
    FIX_ERROR = "fix_error"
    SUGGEST_ALTERNATIVES = "suggest_alternatives"
    REQUEST_CLARIFICATION = "request_clarification"

class AgentState(BaseModel):
    current_task: Optional[str] = None
    last_api_call: Optional[Dict] = None
    error_context: Optional[Dict] = None
    suggested_fixes: List[Dict] = []
    conversation_context: Dict = {}

class BaseAgent:
    """Base class for all agents"""
    def __init__(self):
        self.state = AgentState()

    async def process_message(self, message: str) -> Dict:
        """Process a message and return response"""
        raise NotImplementedError()

    def _plan_actions(self, message: str) -> List[AgentAction]:
        """Determine actions needed based on message"""
        raise NotImplementedError()