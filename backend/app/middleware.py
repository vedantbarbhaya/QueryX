# backend/app/middleware.py
from fastapi import Request
import uuid
from .utils.logger import conversation_id_ctx

def register_middlewares(app):
    """
    Register application-wide middleware.
    """
    @app.middleware("http")
    async def add_conversation_id_middleware(request: Request, call_next):
        """
        Extracts `conversation_id` from POST /api/chat bodies or assigns a new UUID,
        then sets it in the logging context before and after the request.
        """
        conv_id = None
        if request.url.path == "/api/chat" and request.method == "POST":
            try:
                body = await request.json()
                conv_id = body.get("conversation_id")
            except Exception:
                conv_id = None
        if not conv_id:
            conv_id = str(uuid.uuid4())
        conversation_id_ctx.set(conv_id)
        response = await call_next(request)
        response.headers["X-Conversation-ID"] = conv_id
        return response