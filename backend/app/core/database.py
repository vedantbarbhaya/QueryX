from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..config import settings

# SQLAlchemy engine: SQLite with threading support disabled for async context
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
# Create a configured "SessionLocal" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base class for model definitions
Base = declarative_base()

def get_db():
    """Dependency that provides a database session and ensures it's closed after use"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 