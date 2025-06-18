"""
Threat model for WATCHKEEPER Testing Edition.

This module provides the SQLAlchemy model for threat data.
"""

import uuid
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, Enum, func
from sqlalchemy.sql import expression

from src.core.database import Base


class ThreatCategory(str, enum.Enum):
    """Enumeration of threat categories."""
    POLITICAL_UNREST = "political_unrest"
    TRANSPORT_DISRUPTION = "transport_disruption"
    WEATHER_EMERGENCY = "weather_emergency"
    SECURITY_INCIDENT = "security_incident"
    ECONOMIC_IMPACT = "economic_impact"
    HEALTH_EMERGENCY = "health_emergency"


class ThreatStatus(str, enum.Enum):
    """Enumeration of threat statuses."""
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class Threat(Base):
    """
    Threat model representing a potential threat to missionary operations.
    Optimized for SQLite on older hardware.
    """
    __tablename__ = "threats"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    
    # Location data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    country = Column(String(100), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    
    # Threat assessment
    severity = Column(Integer, nullable=False, default=5)  # 1-10
    category = Column(
        Enum(ThreatCategory),
        nullable=False,
        default=ThreatCategory.SECURITY_INCIDENT,
        index=True
    )
    status = Column(
        Enum(ThreatStatus),
        nullable=False,
        default=ThreatStatus.ACTIVE,
        index=True
    )
    confidence_score = Column(Float, nullable=False, default=0.5)  # 0.0-1.0
    missionary_relevance = Column(Integer, nullable=False, default=50)  # 0-100
    
    # Source information
    source_url = Column(String(500), nullable=True)
    source_name = Column(String(100), nullable=True)
    
    # Timestamps
    published_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    def __repr__(self):
        return f"<Threat {self.id}: {self.title}>"
