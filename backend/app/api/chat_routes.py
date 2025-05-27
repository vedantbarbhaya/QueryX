# backend/app/api/chat_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import uuid

from ..core.chat_handler import ChatHandler
from ..utils.logger import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatMessage(BaseModel):
    user_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str = Field(..., alias="response")
    conversation_id: str
    user_id: str = Field(..., alias="user_id")

    class Config:
        allow_population_by_field_name = True

# Initialize the chat handler
chat_handler = ChatHandler()

@router.post("", response_model=ChatResponse)
async def chat(message: ChatMessage):
    try:
        conv_id = message.conversation_id or str(uuid.uuid4())
        result = await chat_handler.get_response(
            user_id=message.user_id,
            message=message.message,
            conversation_id=conv_id
        )
        # Return response with user_id included
        return {
            "response": result["response"],
            "conversation_id": result["conversation_id"],
            "user_id": message.user_id
        }
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )