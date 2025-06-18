"""
Performance monitoring utilities for WATCHKEEPER Testing Edition.

This module provides basic performance monitoring for Mac Mini.
"""

import os
import time
import platform
import psutil
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import threading
import sqlite3
import json

from src.core.logging import logger
from src.core.config import settings


class PerformanceMonitor:
    """
    Performance monitor for WATCHKEEPER Testing Edition.
    
    Provides basic system resource monitoring optimized for Mac Mini.
    """
    
    def __init__(self, sampling_interval: int = 60, history_size: int = 60):
        """
        Initialize the performance monitor.
        
        Args:
            sampling_interval: Interval between samples in seconds.
            history_size: Number of samples to keep in history.
        """
        self.sampling_interval = sampling_interval
        self.history_size = history_size
        self.history = []
        self.running = False
        self.thread = None
        self.start_time = datetime.utcnow()
        
        # System info
        self.system_info = self._get_system_info()
        
        # Database metrics
        self.db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        
        # Create logs directory if it doesn't exist
        os.makedirs("data/logs", exist_ok=True)
        
        # Performance log file
        self.log_file = "data/logs/performance.json"
    
    def _get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            System information.
        """
        try:
            # Get CPU info
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else None,
                "architecture": platform.machine()
            }
            
            # Get memory info
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "total_gb": round(memory.total / (1024**3), 2)
            }
            
            # Get disk info
            disk = psutil.disk_usage("/")
            disk_info = {
                "total": disk.total,
                "total_gb": round(disk.total / (1024**3), 2)
            }
            
            # Get OS info
            os_info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "platform": platform.platform()
            }
            
            # Get Python info
            python_info = {
                "version": platform.python_version(),
                "implementation": platform.python_implementation()
            }
            
            return {
                "hostname": platform.node(),
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "os": os_info,
                "python": python_info
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """
        Collect system metrics.
        
        Returns:
            System metrics.
        """
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                cpu_freq = cpu_freq.current
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_usage = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            }
            
            # Get disk usage
            disk = psutil.disk_usage("/")
            disk_usage = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
            
            # Get network stats
            net_io = psutil.net_io_counters()
            network = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
            
            # Get process info for this process
            process = psutil.Process(os.getpid())
            process_info = {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_percent": process.memory_percent(),
                "memory_rss": process.memory_info().rss,
                "threads": process.num_threads(),
                "open_files": len(process.open_files())
            }
            
            # Get database size
            db_size = 0
            if os.path.exists(self.db_path):
                db_size = os.path.getsize(self.db_path)
            
            # Get database metrics
            db_metrics = self._get_db_metrics()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                "cpu": {
                    "percent": cpu_percent,
                    "frequency": cpu_freq
                },
                "memory": memory_usage,
                "disk": disk_usage,
                "network": network,
                "process": process_info,
                "database": {
                    "size_bytes": db_size,
                    "metrics": db_metrics
                }
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def _get_db_metrics(self) -> Dict[str, Any]:
        """
        Get database metrics.
        
        Returns:
            Database metrics.
        """
        metrics = {}
        
        try:
            if not os.path.exists(self.db_path):
                return {"error": "Database file not found"}
            
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table counts
            tables = ["threats", "sources", "alpha_feedback"]
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    metrics[f"{table}_count"] = count
                except sqlite3.Error:
                    metrics[f"{table}_count"] = 0
            
            # Get database statistics
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            metrics["page_count"] = page_count
            metrics["page_size"] = page_size
            metrics["db_size_calc"] = page_count * page_size
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error getting database metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics
    
    def _monitoring_thread(self):
        """Background thread for continuous monitoring."""
        while self.running:
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                
                # Add to history
                self.history.append(metrics)
                
                # Trim history if needed
                if len(self.history) > self.history_size:
                    self.history = self.history[-self.history_size:]
                
                # Save to log file periodically (every 10 samples)
                if len(self.history) % 10 == 0:
                    self._save_metrics()
                
            except Exception as e:
                logger.error(f"Error in monitoring thread: {e}")
            
            # Sleep until next sample
            time.sleep(self.sampling_interval)
    
    def _save_metrics(self):
        """Save metrics to log file."""
        try:
            # Create a summary of recent metrics
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "system_info": self.system_info,
                "metrics_history": self.history[-10:]  # Save last 10 samples
            }
            
            # Write to log file
            with open(self.log_file, "w") as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def start(self):
        """Start the performance monitor."""
        if self.running:
            logger.warning("Performance monitor already running")
            return
        
        logger.info("Starting performance monitor")
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_thread, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the performance monitor."""
        if not self.running:
            logger.warning("Performance monitor not running")
            return
        
        logger.info("Stopping performance monitor")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        # Save final metrics
        self._save_metrics()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Current system metrics.
        """
        return self._collect_metrics()
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """
        Get metrics history.
        
        Returns:
            Metrics history.
        """
        return self.history
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            System information.
        """
        return self.system_info
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage summary.
        
        Returns:
            Resource usage summary.
        """
        metrics = self._collect_metrics()
        
        return {
            "cpu_percent": metrics["cpu"]["percent"],
            "memory_percent": metrics["memory"]["percent"],
            "disk_percent": metrics["disk"]["percent"],
            "process_cpu_percent": metrics["process"]["cpu_percent"],
            "process_memory_percent": metrics["process"]["memory_percent"],
            "uptime_hours": metrics["uptime_seconds"] / 3600
        }


# Create global instance
performance_monitor = PerformanceMonitor()
