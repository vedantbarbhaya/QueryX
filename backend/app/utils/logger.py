# backend/app/utils/logger.py
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os
import time
# Structured logging
from pythonjsonlogger import jsonlogger

import contextvars

# ContextVar to store current conversation ID for logs
conversation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "conversation_id", default="null"
)

class ContextFilter(logging.Filter):
    """Inject conversation_id from contextvar into log records."""
    def filter(self, record):
        record.conversation_id = conversation_id_ctx.get()
        return True

def setup_logger(name="api_assistant"):
    """
    Set up a logger with console and file handlers using structured JSON logging.
    Args:
        name: Logger name
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a JSON formatter for structured logs
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s %(conversation_id)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(ContextFilter())
    # Create file handler with rotation
    log_dir = Path(__file__).parent.parent / "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Add timestamp to log filename for uniqueness
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"app_{timestamp}.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=10
    )
    file_handler.addFilter(ContextFilter())
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info(f"Logger initialized. Log file: {log_file}")
    return logger

# Create the logger instance
logger = setup_logger()