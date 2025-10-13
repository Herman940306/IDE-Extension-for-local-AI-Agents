"""
Enterprise AI Agents Integration - Backend Service
Project Creator: Herman Swanepoel
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.models import Task
from src.services.connection_manager import ConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global connection manager
connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Enterprise AI Agents Backend starting...")
    logger.info("Project Creator: Herman Swanepoel")
    yield
    logger.info("👋 Enterprise AI Agents Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Enterprise AI Agents API",
    description="Backend service for multi-agent AI coding assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Enterprise AI Agents API",
        "version": "1.0.0",
        "creator": "Herman Swanepoel",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connections": connection_manager.get_connection_count(),
        "service": "backend"
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication"""
    await connection_manager.connect(websocket, client_id)
    
    try:
        # Send welcome message
        await connection_manager.send_personal_message(
            {
                "type": "connection_established",
                "payload": {
                    "client_id": client_id,
                    "message": "Connected to Enterprise AI Agents Backend",
                    "timestamp": asyncio.get_event_loop().time()
                }
            },
            client_id
        )
        
        # Message handling loop
        while True:
            try:
                data = await websocket.receive_json()
                await connection_manager.handle_message(client_id, data)
                
                message_type = data.get("type")
                payload = data.get("payload", {})
                
                logger.info(f"Received message from {client_id}: type={message_type}")
                
                if message_type == "task_request":
                    await handle_task_request(client_id, payload)
                elif message_type == "ping":
                    await handle_ping(client_id)
                elif message_type == "mode_change":
                    await handle_mode_change(client_id, payload)
                else:
                    await connection_manager.send_personal_message(
                        {
                            "type": "error",
                            "payload": {"message": f"Unknown message type: {message_type}"}
                        },
                        client_id
                    )
                    
            except ValidationError as e:
                logger.error(f"Validation error from {client_id}: {e}")
                await connection_manager.send_personal_message(
                    {"type": "error", "payload": {"message": "Invalid message format", "details": str(e)}},
                    client_id
                )
            except Exception as e:
                logger.error(f"Error processing message from {client_id}: {e}")
                await connection_manager.send_personal_message(
                    {"type": "error", "payload": {"message": "Internal server error", "details": str(e)}},
                    client_id
                )
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
        await connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Unexpected error for client {client_id}: {e}")
        await connection_manager.disconnect(client_id)


async def handle_task_request(client_id: str, payload: Dict):
    """Handle task request from client"""
    try:
        task = Task(**payload)
        logger.info(f"Processing task {task.id} of type {task.type} for client {client_id}")
        
        await connection_manager.send_personal_message(
            {
                "type": "task_acknowledged",
                "payload": {
                    "task_id": task.id,
                    "status": "received",
                    "message": "Task received and queued for processing"
                }
            },
            client_id
        )
        
        await asyncio.sleep(0.1)
        
        await connection_manager.send_personal_message(
            {
                "type": "agent_response",
                "payload": {
                    "task_id": task.id,
                    "agent_id": "mock_agent",
                    "agent_name": "Mock Agent",
                    "suggestions": [],
                    "confidence": 0.0,
                    "reasoning": "Agent orchestration not yet implemented"
                }
            },
            client_id
        )
        
    except ValidationError as e:
        logger.error(f"Invalid task payload from {client_id}: {e}")
        await connection_manager.send_personal_message(
            {"type": "error", "payload": {"message": "Invalid task format", "details": str(e)}},
            client_id
        )


async def handle_ping(client_id: str):
    """Handle ping message"""
    await connection_manager.send_personal_message(
        {"type": "pong", "payload": {"timestamp": asyncio.get_event_loop().time()}},
        client_id
    )


async def handle_mode_change(client_id: str, payload: Dict):
    """Handle mode change request (offline/online)"""
    mode = payload.get("mode", "offline")
    logger.info(f"Client {client_id} changed mode to: {mode}")
    
    await connection_manager.send_personal_message(
        {
            "type": "mode_changed",
            "payload": {
                "mode": mode,
                "message": f"Mode changed to {mode}",
                "timestamp": asyncio.get_event_loop().time()
            }
        },
        client_id
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Enterprise AI Agents Backend Server")
    logger.info("Project Creator: Herman Swanepoel")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
