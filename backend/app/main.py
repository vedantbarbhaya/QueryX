# backend/app/main.py
from fastapi import FastAPI, Depends, Query
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .utils.logger import logger, conversation_id_ctx
from .config import settings

from .api.chat_routes import router as chat_router
from .api.document_routes import router as documents_router
from .api.health_routes import router as health_router
from .api.conversation_routes import router as conversations_router
from .api.auth_routes import router as auth_router
from .middleware import register_middlewares

# Import RAG components
from .rag.vector_store import VectorStoreManager

# OutboxFlusher and ConversationStore for lifecycle-managed background flush
from .core.outbox_flusher import OutboxFlusher
from .core.conversation_store import SQLiteConversationStore

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the outbox flusher
    flusher.start()
    yield
    # Stop and flush remaining messages
    flusher.stop()

app = FastAPI(
    title="API Documentation Assistant",
    description="An AI-powered assistant for exploring and understanding API documentation",
    version="1.0.0",
    lifespan=lifespan
)

# Instantiate store and flusher for outbox background flush
store = SQLiteConversationStore("conversations.db")
flusher = OutboxFlusher(store)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(url) for url in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_middlewares(app)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(conversations_router)
app.include_router(auth_router)

@app.on_event("startup")
def on_startup():
    # Create all database tables
    from .core.database import engine
    from .core.models import Base
    Base.metadata.create_all(bind=engine)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )

# Run the application (optional: for local dev only, flusher is managed by FastAPI events)
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API Documentation Assistant server")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)