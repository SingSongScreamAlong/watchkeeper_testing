"""
Logging configuration for WATCHKEEPER Testing Edition.

This module provides a simple logging setup optimized for testing.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

from src.core.config import settings

# Create logs directory if it doesn't exist
logs_dir = Path("data/logs")
logs_dir.mkdir(parents=True, exist_ok=True)

# Configure logging
def setup_logging():
    """
    Configure logging for the application.
    
    Creates a logger that logs to both console and file with different levels.
    """
    log_level = getattr(logging, settings.LOG_LEVEL)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs (DEBUG and above)
    file_handler = RotatingFileHandler(
        logs_dir / "watchkeeper.log",
        maxBytes=10_485_760,  # 10MB
        backupCount=5,  # Keep 5 backup logs
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # File handler for errors only
    error_handler = RotatingFileHandler(
        logs_dir / "error.log",
        maxBytes=10_485_760,  # 10MB
        backupCount=5,  # Keep 5 backup logs
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    return root_logger

# Create logger instance
logger = setup_logging()
