"""
Database configuration for WATCHKEEPER Testing Edition.

This module provides SQLite database setup optimized for a 2014 Mac Mini.
"""

import os
from typing import Generator
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

from src.core.config import settings

# Create SQLite engine with optimizations for older hardware
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    pool_pre_ping=True,  # Check connection before using from pool
    pool_size=5,  # Small pool size for limited resources
    max_overflow=10,  # Limited overflow for peak demand
    pool_recycle=1800,  # Recycle connections after 30 minutes
    echo=False,  # Disable SQL logging for performance
)

# Enable SQLite foreign key support
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and performance
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative value means KB)
        cursor.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        cursor.close()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_db() -> Generator:
    """
    Get database session.
    
    Yields:
        Session: Database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Initialize database by creating all tables.
    """
    # Import all models here to ensure they are registered with Base
    from src.models.threat import Threat
    from src.models.source import Source
    from src.models.feedback import AlphaFeedback
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    print(f"Database initialized at {settings.DATABASE_URL.replace('sqlite:///', '')}")
