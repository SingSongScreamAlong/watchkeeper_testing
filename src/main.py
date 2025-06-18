"""
Main application for WATCHKEEPER Testing Edition.

This module sets up the FastAPI application with CORS and WebSocket integration.
"""

import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import uvicorn
from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.logging import logger
from src.core.database import init_db, engine, Base
from src.api.threats import router as threats_router
from src.api.health import router as health_router
from src.api.testing import router as testing_router
from src.api.websocket import router as websocket_router
from src.services.news_collector import collection_manager
from src.utils.performance import performance_monitor


# API key security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Depends(api_key_header)):
    """
    Validate API key.
    
    Args:
        api_key_header: API key from header.
        
    Returns:
        API key if valid.
        
    Raises:
        HTTPException: If API key is invalid.
    """
    if api_key_header == settings.API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for the FastAPI application.
    
    Args:
        app: FastAPI application.
    """
    # Startup
    logger.info("Starting WATCHKEEPER Testing Edition")
    
    # Initialize database
    logger.info("Initializing database")
    await init_db()
    
    # Start performance monitor
    logger.info("Starting performance monitor")
    performance_monitor.start()
    
    # Initialize collection manager
    logger.info("Initializing collection manager")
    await collection_manager.initialize()
    
    # Schedule collections
    logger.info("Scheduling collections")
    collection_manager.schedule_collections()
    
    yield
    
    # Shutdown
    logger.info("Shutting down WATCHKEEPER Testing Edition")
    
    # Close collection manager session
    logger.info("Closing collection manager session")
    await collection_manager.close()
    
    # Stop performance monitor
    logger.info("Stopping performance monitor")
    performance_monitor.stop()


# Create FastAPI app
app = FastAPI(
    title="WATCHKEEPER Testing Edition",
    description="Lightweight AI-powered intelligence platform for small-scale testing and proof-of-concept validation.",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns:
        Basic API information.
    """
    return {
        "name": "WATCHKEEPER Testing Edition",
        "version": "0.1.0",
        "description": "Lightweight AI-powered intelligence platform for small-scale testing and proof-of-concept validation."
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler.
    
    Args:
        request: Request that caused the exception.
        exc: Exception that was raised.
        
    Returns:
        JSON response with error details.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(
    threats_router,
    prefix="/api/threats",
    tags=["Threats"],
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    health_router,
    prefix="/api/health",
    tags=["Health"]
)

app.include_router(
    testing_router,
    prefix="/api/testing",
    tags=["Testing"],
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    websocket_router,
    tags=["WebSocket"]
)


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
