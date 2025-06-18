"""
Source model for WATCHKEEPER Testing Edition.

This module provides the SQLAlchemy model for news source data.
"""

import uuid
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Enum, func
from sqlalchemy.sql import expression

from src.core.database import Base


class SourceType(str, enum.Enum):
    """Enumeration of source types."""
    RSS_FEED = "rss_feed"
    WEB_SCRAPE = "web_scrape"


class Source(Base):
    """
    Source model representing a news source for intelligence collection.
    Optimized for SQLite on older hardware.
    """
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True, index=True)
    url = Column(String(500), nullable=False, unique=True)
    source_type = Column(
        Enum(SourceType),
        nullable=False,
        default=SourceType.RSS_FEED,
        index=True
    )
    
    # Source assessment
    reliability_score = Column(Float, nullable=False, default=0.8)  # 0.0-1.0
    language = Column(String(10), nullable=False, default="en")
    country = Column(String(50), nullable=True)
    
    # Collection metadata
    last_collected_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    collection_frequency = Column(Integer, nullable=False, default=30)  # minutes
    rate_limit_per_hour = Column(Integer, nullable=False, default=60)
    
    # Collection statistics
    total_articles_collected = Column(Integer, nullable=False, default=0)
    successful_collections = Column(Integer, nullable=False, default=0)
    failed_collections = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Source {self.id}: {self.name}>"
    
    @property
    def success_rate(self):
        """Calculate the success rate of collections."""
        total = self.successful_collections + self.failed_collections
        if total == 0:
            return 0.0
        return self.successful_collections / total
