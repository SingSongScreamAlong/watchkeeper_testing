#!/usr/bin/env python3
"""
Testing runner script for WATCHKEEPER Testing Edition.

This script runs the WATCHKEEPER Testing Edition with a scheduler.
"""

import os
import sys
import asyncio
import signal
import time
from datetime import datetime, timedelta
import schedule
import uvicorn
import threading
import argparse

from src.core.config import settings
from src.core.logging import logger
from src.core.database import init_db
from src.services.news_collector import collection_manager
from src.utils.performance import performance_monitor


# Flag to control the main loop
running = True


def signal_handler(sig, frame):
    """Handle termination signals."""
    global running
    print("\nShutting down gracefully...")
    running = False


async def run_initial_collection():
    """Run initial collection on startup."""
    logger.info("Running initial collection")
    try:
        result = await collection_manager.run_collection()
        logger.info(f"Initial collection complete: {result}")
    except Exception as e:
        logger.error(f"Error in initial collection: {e}")


def run_scheduler():
    """Run the scheduler in a separate thread."""
    logger.info("Starting scheduler thread")
    while running:
        schedule.run_pending()
        time.sleep(1)


async def main():
    """Main entry point."""
    global running
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="WATCHKEEPER Testing Edition runner")
    parser.add_argument("--no-api", action="store_true", help="Don't start the API server")
    parser.add_argument("--no-collection", action="store_true", help="Don't run news collection")
    parser.add_argument("--no-monitor", action="store_true", help="Don't run performance monitoring")
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Print banner
        print("\n" + "=" * 80)
        print(f"WATCHKEEPER Testing Edition v0.1.0")
        print(f"Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")
        
        # Initialize database
        logger.info("Initializing database")
        await init_db()
        
        # Start performance monitoring if enabled
        if not args.no_monitor:
            logger.info("Starting performance monitor")
            performance_monitor.start()
        
        # Initialize collection manager if collection is enabled
        if not args.no_collection:
            logger.info("Initializing collection manager")
            await collection_manager.initialize()
            
            # Schedule collections
            logger.info(f"Scheduling collections every {settings.COLLECTION_FREQUENCY} minutes")
            collection_manager.schedule_collections()
            
            # Start scheduler thread
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            
            # Run initial collection
            await run_initial_collection()
        
        # Start API server if enabled
        if not args.no_api:
            logger.info(f"Starting API server on {settings.API_HOST}:{settings.API_PORT}")
            config = uvicorn.Config(
                "src.main:app",
                host=settings.API_HOST,
                port=settings.API_PORT,
                log_level="info",
                reload=settings.DEBUG
            )
            server = uvicorn.Server(config)
            await server.serve()
        else:
            # If API server is not running, keep the main thread alive
            logger.info("API server disabled, running in collection-only mode")
            while running:
                await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Cleaning up resources")
        
        if not args.no_collection:
            logger.info("Closing collection manager")
            await collection_manager.close()
        
        if not args.no_monitor:
            logger.info("Stopping performance monitor")
            performance_monitor.stop()
        
        logger.info("Shutdown complete")


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
