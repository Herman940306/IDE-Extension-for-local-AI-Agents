"""
API module for REST and WebSocket endpoints
Project Creator: Herman Swanepoel
"""

from .v2_routes import router as v2_router

__all__ = ["v2_router"]
