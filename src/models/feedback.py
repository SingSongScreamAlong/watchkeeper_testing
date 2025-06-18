"""
Feedback model for WATCHKEEPER Testing Edition.

This module provides the SQLAlchemy model for alpha testing feedback.
"""

import uuid
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Enum, func
from sqlalchemy.sql import expression

from src.core.database import Base


class FeedbackType(str, enum.Enum):
    """Enumeration of feedback types."""
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    FALSE_POSITIVE = "false_positive"
    MISSING_THREAT = "missing_threat"


class AlphaFeedback(Base):
    """
    AlphaFeedback model for collecting feedback during alpha testing.
    """
    __tablename__ = "alpha_feedback"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    threat_id = Column(String(36), ForeignKey("threats.id"), nullable=True)
    user_identifier = Column(String(100), nullable=False, index=True)  # anonymous but trackable
    
    # Feedback data
    feedback_type = Column(
        Enum(FeedbackType),
        nullable=False,
        index=True
    )
    rating = Column(Integer, nullable=False)  # 1-5
    comments = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AlphaFeedback {self.id}: {self.feedback_type.value}>"
