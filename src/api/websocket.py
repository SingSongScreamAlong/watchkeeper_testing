"""
WebSocket API for WATCHKEEPER Testing Edition.

This module provides WebSocket endpoints for real-time updates.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.logging import logger
from src.models.threat import Threat, ThreatStatus, ThreatCategory

router = APIRouter()

# Store connected clients
class ConnectionManager:
    """
    WebSocket connection manager.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_subscriptions: Dict[WebSocket, List[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, topics: List[str]):
        """
        Connect a WebSocket client.
        
        Args:
            websocket: WebSocket connection.
            client_id: Client identifier.
            topics: List of topics to subscribe to.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_subscriptions[websocket] = topics
        logger.info(f"Client {client_id} connected to WebSocket. Topics: {topics}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "topics": topics,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client.
        
        Args:
            websocket: WebSocket connection.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if websocket in self.client_subscriptions:
            del self.client_subscriptions[websocket]
    
    async def broadcast(self, message: Dict[str, Any], topic: str = "all"):
        """
        Broadcast a message to all connected clients subscribed to the topic.
        
        Args:
            message: Message to broadcast.
            topic: Topic to broadcast to.
        """
        # Add timestamp to message
        message["timestamp"] = datetime.utcnow().isoformat()
        
        # Broadcast to all clients subscribed to the topic
        for websocket, topics in self.client_subscriptions.items():
            if topic == "all" or topic in topics or "all" in topics:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")
                    # We'll handle disconnection in the main WebSocket handler


# Create connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(...),
    topics: str = Query("all")
):
    """
    WebSocket endpoint for real-time updates.
    
    Args:
        websocket: WebSocket connection.
        client_id: Client identifier.
        topics: Comma-separated list of topics to subscribe to.
    """
    # Parse topics
    topic_list = topics.split(",")
    
    # Connect client
    await manager.connect(websocket, client_id, topic_list)
    
    try:
        # Keep connection alive and handle messages
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            
            try:
                # Parse message
                message = json.loads(data)
                
                # Handle message
                if message.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif message.get("type") == "subscribe":
                    # Update subscriptions
                    new_topics = message.get("topics", [])
                    if isinstance(new_topics, list):
                        manager.client_subscriptions[websocket] = new_topics
                        await websocket.send_json({
                            "type": "subscription_updated",
                            "topics": new_topics,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "message": "Unknown message type",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except json.JSONDecodeError:
                # Invalid JSON
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        # Client disconnected
        manager.disconnect(websocket)
        logger.info(f"Client {client_id} disconnected from WebSocket")
    except Exception as e:
        # Other error
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Function to broadcast a new threat
async def broadcast_new_threat(threat: Threat):
    """
    Broadcast a new threat to all connected clients.
    
    Args:
        threat: Threat to broadcast.
    """
    await manager.broadcast({
        "type": "new_threat",
        "data": {
            "id": threat.id,
            "title": threat.title,
            "description": threat.description,
            "severity": threat.severity,
            "category": threat.category.value,
            "status": threat.status.value,
            "country": threat.country,
            "city": threat.city,
            "latitude": threat.latitude,
            "longitude": threat.longitude,
            "created_at": threat.created_at.isoformat()
        }
    }, "threats")


# Function to broadcast a threat update
async def broadcast_threat_update(threat: Threat):
    """
    Broadcast a threat update to all connected clients.
    
    Args:
        threat: Updated threat to broadcast.
    """
    await manager.broadcast({
        "type": "threat_update",
        "data": {
            "id": threat.id,
            "title": threat.title,
            "status": threat.status.value,
            "severity": threat.severity,
            "updated_at": threat.updated_at.isoformat()
        }
    }, "threats")


# Function to broadcast system status
async def broadcast_system_status(status: Dict[str, Any]):
    """
    Broadcast system status to all connected clients.
    
    Args:
        status: System status to broadcast.
    """
    await manager.broadcast({
        "type": "system_status",
        "data": status
    }, "system")
