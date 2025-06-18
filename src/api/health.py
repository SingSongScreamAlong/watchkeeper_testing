"""
Health API endpoints for WATCHKEEPER Testing Edition.

This module provides endpoints for system health monitoring.
"""

import os
import platform
import psutil
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends

from src.core.config import settings
from src.core.logging import logger

router = APIRouter()


async def check_ollama_health() -> Dict[str, Any]:
    """
    Check if Ollama is running and responding.
    
    Returns:
        Dict[str, Any]: Status information about Ollama.
    """
    try:
        import requests
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL}/api/version",
            timeout=5
        )
        if response.status_code == 200:
            return {
                "status": "operational",
                "version": response.json().get("version", "unknown"),
                "model": settings.AI_MODEL
            }
        return {
            "status": "degraded",
            "error": f"Ollama responded with status code {response.status_code}"
        }
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return {
            "status": "unavailable",
            "error": str(e)
        }


async def check_database_health() -> Dict[str, Any]:
    """
    Check if the database is accessible.
    
    Returns:
        Dict[str, Any]: Status information about the database.
    """
    try:
        from sqlalchemy import text
        from src.core.database import engine
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            connection.commit()
            
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        return {
            "status": "operational",
            "size_mb": round(db_size / (1024 * 1024), 2),
            "path": db_path
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unavailable",
            "error": str(e)
        }


async def get_last_collection_time() -> Dict[str, Any]:
    """
    Get the timestamp of the last collection run.
    
    Returns:
        Dict[str, Any]: Information about the last collection.
    """
    try:
        from sqlalchemy import func, desc
        from sqlalchemy.orm import Session
        from src.core.database import SessionLocal
        from src.models.source import Source
        
        db = SessionLocal()
        try:
            last_collection = db.query(
                func.max(Source.last_collected_at)
            ).scalar()
            
            if last_collection:
                return {
                    "last_collection": last_collection.isoformat(),
                    "age_minutes": round((datetime.utcnow() - last_collection).total_seconds() / 60)
                }
            return {
                "last_collection": None,
                "age_minutes": None
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to get last collection time: {e}")
        return {
            "last_collection": None,
            "error": str(e)
        }


async def get_system_stats() -> Dict[str, Any]:
    """
    Get system resource statistics.
    
    Returns:
        Dict[str, Any]: System resource statistics.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024 ** 3), 2),
            "memory_total_gb": round(memory.total / (1024 ** 3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "platform": platform.platform(),
            "python_version": platform.python_version()
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return {
            "error": str(e)
        }


@router.get("/")
async def health_check():
    """
    System health check endpoint.
    
    Returns:
        Dict: Health status of various system components.
    """
    return {
        "status": "operational",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "ollama_status": await check_ollama_health(),
        "database_status": await check_database_health(),
        "last_collection": await get_last_collection_time(),
        "system": await get_system_stats()
    }
