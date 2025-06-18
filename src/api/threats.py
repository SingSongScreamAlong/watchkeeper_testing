"""
Threat API endpoints for WATCHKEEPER Testing Edition.

This module provides endpoints for threat data management.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.core.database import get_db
from src.core.logging import logger
from src.models.threat import Threat, ThreatCategory, ThreatStatus

# Create router
router = APIRouter()


@router.get("/")
async def list_threats(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[ThreatStatus] = None,
    category: Optional[ThreatCategory] = None,
    country: Optional[str] = None,
    min_severity: Optional[int] = None,
    min_confidence: Optional[float] = None,
    days: Optional[int] = None,
    active_only: bool = True
):
    """
    List threats with optional filtering.
    
    Args:
        db: Database session.
        skip: Number of items to skip.
        limit: Maximum number of items to return.
        status: Filter by threat status.
        category: Filter by threat category.
        country: Filter by country.
        min_severity: Minimum severity level.
        min_confidence: Minimum confidence score.
        days: Only include threats from the last N days.
        active_only: Only include active threats.
        
    Returns:
        List of threats.
    """
    query = db.query(Threat)
    
    # Apply filters
    if active_only:
        query = query.filter(Threat.is_active == True)
    
    if status:
        query = query.filter(Threat.status == status)
        
    if category:
        query = query.filter(Threat.category == category)
        
    if country:
        query = query.filter(Threat.country.ilike(f"%{country}%"))
        
    if min_severity is not None:
        query = query.filter(Threat.severity >= min_severity)
        
    if min_confidence is not None:
        query = query.filter(Threat.confidence_score >= min_confidence)
        
    if days is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Threat.created_at >= cutoff_date)
    
    # Order by created_at desc
    query = query.order_by(desc(Threat.created_at))
    
    # Apply pagination
    threats = query.offset(skip).limit(limit).all()
    
    return threats


@router.get("/{threat_id}")
async def get_threat(
    threat_id: str = Path(..., description="The ID of the threat to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Get a specific threat by ID.
    
    Args:
        threat_id: The ID of the threat.
        db: Database session.
        
    Returns:
        Threat object.
        
    Raises:
        HTTPException: If threat not found.
    """
    threat = db.query(Threat).filter(Threat.id == threat_id).first()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")
    
    return threat


@router.get("/map")
async def get_map_threats(
    db: Session = Depends(get_db),
    days: Optional[int] = 7,
    min_severity: Optional[int] = 3,
    status: Optional[ThreatStatus] = None
):
    """
    Get threats for map display with location data.
    
    Args:
        db: Database session.
        days: Only include threats from the last N days.
        min_severity: Minimum severity level.
        status: Filter by threat status.
        
    Returns:
        List of threats with location data.
    """
    query = db.query(Threat).filter(
        Threat.is_active == True,
        Threat.latitude.isnot(None),
        Threat.longitude.isnot(None)
    )
    
    if days is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Threat.created_at >= cutoff_date)
    
    if min_severity is not None:
        query = query.filter(Threat.severity >= min_severity)
        
    if status:
        query = query.filter(Threat.status == status)
    
    threats = query.order_by(desc(Threat.created_at)).all()
    
    return threats


@router.get("/stats")
async def get_threat_stats(
    db: Session = Depends(get_db),
    days: Optional[int] = 30
):
    """
    Get threat statistics.
    
    Args:
        db: Database session.
        days: Calculate stats for the last N days.
        
    Returns:
        Threat statistics.
    """
    # Base query
    query = db.query(Threat)
    
    # Apply time filter if specified
    if days is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Threat.created_at >= cutoff_date)
    
    # Get total count
    total_count = query.count()
    
    # Get counts by status
    status_counts = {}
    for status in ThreatStatus:
        count = query.filter(Threat.status == status).count()
        status_counts[status.value] = count
    
    # Get counts by category
    category_counts = {}
    for category in ThreatCategory:
        count = query.filter(Threat.category == category).count()
        category_counts[category.value] = count
    
    # Get counts by country (top 5)
    country_query = db.query(
        Threat.country, 
        db.func.count(Threat.id).label('count')
    ).group_by(Threat.country).order_by(desc('count')).limit(5)
    
    country_counts = {row.country: row.count for row in country_query if row.country}
    
    # Calculate average severity and confidence
    avg_severity = db.query(db.func.avg(Threat.severity)).scalar() or 0
    avg_confidence = db.query(db.func.avg(Threat.confidence_score)).scalar() or 0
    
    return {
        "total_count": total_count,
        "by_status": status_counts,
        "by_category": category_counts,
        "by_country": country_counts,
        "avg_severity": round(avg_severity, 1),
        "avg_confidence": round(avg_confidence, 2),
        "days": days
    }
