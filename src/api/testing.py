"""
Testing API endpoints for WATCHKEEPER Testing Edition.

This module provides endpoints for alpha testing specific functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.core.database import get_db
from src.core.logging import logger
from src.models.feedback import AlphaFeedback, FeedbackType
from src.models.threat import Threat
from src.models.source import Source

# Create router
router = APIRouter()


@router.get("/stats")
async def get_testing_stats(
    db: Session = Depends(get_db),
    days: Optional[int] = 7
):
    """
    Get alpha testing statistics.
    
    Args:
        db: Database session.
        days: Calculate stats for the last N days.
        
    Returns:
        Testing statistics.
    """
    # Calculate date cutoff
    cutoff_date = datetime.utcnow() - timedelta(days=days if days is not None else 7)
    
    # Get threat stats
    total_threats = db.query(func.count(Threat.id)).scalar()
    recent_threats = db.query(func.count(Threat.id)).filter(
        Threat.created_at >= cutoff_date
    ).scalar()
    
    # Get source stats
    total_sources = db.query(func.count(Source.id)).scalar()
    active_sources = db.query(func.count(Source.id)).filter(
        Source.is_active == True
    ).scalar()
    
    # Get collection stats
    total_articles = db.query(func.sum(Source.total_articles_collected)).scalar() or 0
    
    # Get feedback stats
    total_feedback = db.query(func.count(AlphaFeedback.id)).scalar()
    recent_feedback = db.query(func.count(AlphaFeedback.id)).filter(
        AlphaFeedback.created_at >= cutoff_date
    ).scalar()
    
    # Get average ratings
    avg_rating = db.query(func.avg(AlphaFeedback.rating)).scalar() or 0
    
    # Get feedback by type
    feedback_by_type = {}
    for feedback_type in FeedbackType:
        count = db.query(func.count(AlphaFeedback.id)).filter(
            AlphaFeedback.feedback_type == feedback_type
        ).scalar()
        feedback_by_type[feedback_type.value] = count
    
    return {
        "threats": {
            "total": total_threats,
            "recent": recent_threats
        },
        "sources": {
            "total": total_sources,
            "active": active_sources
        },
        "collection": {
            "total_articles": total_articles
        },
        "feedback": {
            "total": total_feedback,
            "recent": recent_feedback,
            "avg_rating": round(avg_rating, 2),
            "by_type": feedback_by_type
        },
        "time_period_days": days
    }


@router.post("/feedback")
async def submit_feedback(
    feedback: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Submit alpha testing feedback.
    
    Args:
        feedback: Feedback data.
        db: Database session.
        
    Returns:
        Created feedback object.
    """
    # Validate feedback type
    try:
        feedback_type = FeedbackType(feedback.get("feedback_type"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feedback type. Must be one of: {', '.join([t.value for t in FeedbackType])}"
        )
    
    # Validate rating
    rating = feedback.get("rating")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be an integer between 1 and 5"
        )
    
    # Validate threat_id if provided
    threat_id = feedback.get("threat_id")
    if threat_id:
        threat = db.query(Threat).filter(Threat.id == threat_id).first()
        if not threat:
            raise HTTPException(
                status_code=404,
                detail="Threat not found"
            )
    
    # Create feedback object
    new_feedback = AlphaFeedback(
        threat_id=threat_id,
        user_identifier=feedback.get("user_identifier", "anonymous"),
        feedback_type=feedback_type,
        rating=rating,
        comments=feedback.get("comments")
    )
    
    # Save to database
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    
    logger.info(f"New feedback submitted: {new_feedback.id}")
    
    return new_feedback


@router.get("/feedback")
async def list_feedback(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    feedback_type: Optional[FeedbackType] = None,
    min_rating: Optional[int] = None,
    user_identifier: Optional[str] = None,
    days: Optional[int] = None
):
    """
    List alpha testing feedback with optional filtering.
    
    Args:
        db: Database session.
        skip: Number of items to skip.
        limit: Maximum number of items to return.
        feedback_type: Filter by feedback type.
        min_rating: Minimum rating.
        user_identifier: Filter by user identifier.
        days: Only include feedback from the last N days.
        
    Returns:
        List of feedback.
    """
    query = db.query(AlphaFeedback)
    
    # Apply filters
    if feedback_type:
        query = query.filter(AlphaFeedback.feedback_type == feedback_type)
        
    if min_rating is not None:
        query = query.filter(AlphaFeedback.rating >= min_rating)
        
    if user_identifier:
        query = query.filter(AlphaFeedback.user_identifier == user_identifier)
        
    if days is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AlphaFeedback.created_at >= cutoff_date)
    
    # Order by created_at desc
    query = query.order_by(desc(AlphaFeedback.created_at))
    
    # Apply pagination
    feedback_list = query.offset(skip).limit(limit).all()
    
    return feedback_list


@router.post("/trigger-collection")
async def trigger_collection(
    background_tasks: BackgroundTasks,
    source_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Trigger a manual collection run.
    
    Args:
        background_tasks: FastAPI background tasks.
        source_id: Optional source ID to collect from a specific source.
        db: Database session.
        
    Returns:
        Status message.
    """
    # This is a placeholder that will be implemented when the collection service is ready
    # For now, we'll just return a success message
    
    if source_id:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(
                status_code=404,
                detail="Source not found"
            )
        source_name = source.name
    else:
        source_name = "all sources"
    
    # Log the request
    logger.info(f"Manual collection triggered for {source_name}")
    
    # In the future, this will add a background task to run the collection
    # background_tasks.add_task(run_collection, source_id)
    
    return {
        "status": "collection_triggered",
        "message": f"Collection triggered for {source_name}",
        "timestamp": datetime.utcnow().isoformat()
    }
