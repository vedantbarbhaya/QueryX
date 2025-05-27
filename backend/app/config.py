# backend/app/config.py
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, AnyUrl

BASE_DIR = Path(__file__).parent

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    CHAT_MODEL: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.5
    MAX_TOKENS: int = 1000

    VECTOR_STORE_CHUNK_SIZE: int = 1000
    VECTOR_STORE_CHUNK_OVERLAP: int = 200
    K_RETRIEVAL: int = 5

    CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:5173",
        "http://localhost:3000"
    ]
    API_TOKEN: str = "your_api_token_here"

    RABBITMQ_URL: AnyUrl = 'amqp://guest:guest@localhost:5672/%2F'

    REDIS_URL: AnyUrl = 'redis://localhost:6379/0'
    CACHE_TTL_SECONDS: int = 3600
    MAX_CACHE_LENGTH: int = 50

    # Database URL for SQLAlchemy (using the same SQLite file for users and conversations)
    DATABASE_URL: str = f"sqlite:///{BASE_DIR.parent / 'conversations.db'}"

    # JWT configuration
    SECRET_KEY: str  # secret key for signing JWTs (set in .env)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = BASE_DIR.parent / ".env"
        case_sensitive = True

    

settings = Settings()
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
VECTOR_STORE_DIR = BASE_DIR / "vector_store" / "faiss_index"