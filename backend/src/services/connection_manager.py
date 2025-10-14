"""
WebSocket connection manager
Project Creator: Herman Swanepoel
"""

import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = {
                "connected_at": asyncio.get_event_loop().time(),
                "messages_sent": 0,
                "messages_received": 0,
            }
        logger.info(
            f"Client {client_id} connected. Total connections: {len(self.active_connections)}"
        )

    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection"""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                metadata = self.connection_metadata.pop(client_id, {})
                logger.info(
                    f"Client {client_id} disconnected. "
                    f"Messages sent: {metadata.get('messages_sent', 0)}, "
                    f"received: {metadata.get('messages_received', 0)}"
                )

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
                self.connection_metadata[client_id]["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                await self.disconnect(client_id)

    async def broadcast(self, message: dict, exclude: Set[str] = None) -> None:
        """Broadcast a message to all connected clients"""
        exclude = exclude or set()
        disconnected = []

        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                try:
                    await websocket.send_json(message)
                    self.connection_metadata[client_id]["messages_sent"] += 1
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)

    def get_client_metadata(self, client_id: str) -> dict:
        """Get metadata for a specific client"""
        return self.connection_metadata.get(client_id, {})

    async def handle_message(self, client_id: str, message: dict) -> None:
        """Handle incoming message from client"""
        if client_id in self.connection_metadata:
            self.connection_metadata[client_id]["messages_received"] += 1
