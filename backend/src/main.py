"""
Enterprise AI Agents Integration - Backend Service
Project Creator: Herman Swanepoel
"""

import asyncio
import inspect
import time
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Dict, Optional, cast

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import ValidationError

from src.api.exception_handlers import register_exception_handlers
from src.api.middleware import (
    CorrelationIDMiddleware,
    RateLimitMiddleware,
    RequestSizeMiddleware,
)
from src.core.config import get_settings
from src.core.container import Container
from src.core.logging import configure_logging, get_logger
from src.models.session import (
    TaskAcceptedPayload,
    TaskRequestPayload,
    TaskSessionResult,
)
from src.services.connection_manager import ConnectionManager

# Configure structured logging
settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Global services
connection_manager = ConnectionManager()
container: Optional[Container] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global container

    logger.info("backend_starting", creator="Herman Swanepoel")

    # Initialize DI container
    local_container = Container()
    container = local_container
    logger.info("container_initialized")

    try:
        redis = local_container.redis_client()
        if inspect.isawaitable(redis):
            redis = await cast(Awaitable[Any], redis)

        if redis:
            ping_result = redis.ping()
            if inspect.isawaitable(ping_result):
                await ping_result
            logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))

    yield

    logger.info("backend_shutting_down")
    try:
        await local_container.redis_pool().close()
    except Exception as e:
        logger.warning(f"Error closing redis pool: {e}")


# Create FastAPI application
API_DESCRIPTION = "Backend service for multi-agent AI coding assistant with production-ready infrastructure."  # noqa: E501

app = FastAPI(
    title="Enterprise AI Agents API",
    description=API_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "health", "description": "Health check and system status endpoints"},
        {"name": "websocket", "description": "Real-time WebSocket communication"},
        {"name": "cache", "description": "Cache management and statistics"},
    ],
    contact={
        "name": "Herman Swanepoel",
        "url": "https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents",
    },
    license_info={
        "name": "MIT",
    },
)

# Register exception handlers
register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters: first added = last executed)
# 1. Correlation ID (first to execute, adds ID to all requests)
app.add_middleware(CorrelationIDMiddleware)

# 2. Request Size Validation (check size before processing)
app.add_middleware(RequestSizeMiddleware, max_size=settings.max_request_size)


# --- Prometheus metrics ---
# Basic HTTP metrics: request counts and durations by method/path/status
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "path", "status_code"],
    buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10),
)


@app.middleware("http")
async def prometheus_http_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    method = request.method
    status = str(response.status_code)
    # record
    REQUEST_COUNT.labels(method=method, path=path, status_code=status).inc()
    REQUEST_LATENCY.labels(
        method=method,
        path=path,
        status_code=status,
    ).observe(elapsed)
    return response


@app.get("/metrics", include_in_schema=False)
def metrics_endpoint() -> Response:
    """Prometheus scrape endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(
    "/",
    summary="API Root",
    description="Get basic API information and status",
    response_description="API information including version and status",
    tags=["health"],
)
async def root():
    """
    Get API root information.

    Returns basic information about the API including:
    - Service name
    - Version
    - Creator
    - Status
    - Documentation links
    """
    return {
        "service": "Enterprise AI Agents API",
        "version": "1.0.0",
        "creator": "Herman Swanepoel",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint with component status

    Returns comprehensive health status including:
    - Overall service status
    - Redis connection status
    - Cache statistics
    - Active connections
    """
    health_status = {
        "status": "healthy",
        "service": "backend",
        "connections": connection_manager.get_connection_count(),
        "components": {},
    }

    if container is None:
        health_status["components"]["redis"] = "disabled"
        health_status["components"]["cache"] = {"enabled": False}
        return health_status

    try:
        redis = container.redis_client()
        if inspect.isawaitable(redis):
            redis = await cast(Awaitable[Any], redis)

        if redis:
            try:
                ping_result = redis.ping()
                if inspect.isawaitable(ping_result):
                    await ping_result
                health_status["components"]["redis"] = "healthy"
            except Exception:
                health_status["components"]["redis"] = "unhealthy"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["redis"] = "disabled"
    except Exception:
        health_status["components"]["redis"] = "disabled"

    try:
        cache_stats = await container.response_cache().get_stats()
        health_status["components"]["cache"] = cache_stats
    except Exception:
        health_status["components"]["cache"] = {"enabled": False}

    return health_status


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication"""
    connected = False

    try:
        await connection_manager.connect(websocket, client_id)
        connected = True
        logger.info("websocket_connected", client_id=client_id)

        # Send welcome message
        await connection_manager.send_personal_message(
            {
                "type": "connection_established",
                "payload": {
                    "client_id": client_id,
                    "message": "Connected to Enterprise AI Agents Backend",
                    "timestamp": asyncio.get_event_loop().time(),
                },
            },
            client_id,
        )
    except Exception as e:
        logger.error("websocket_connection_failed", client_id=client_id, error=str(e))
        return

    disconnect_reason = "unknown"

    try:
        # Message handling loop
        while True:
            try:
                data = await websocket.receive_json()
                await connection_manager.handle_message(client_id, data)

                message_type = data.get("type")
                payload = data.get("payload", {})

                logger.info(
                    "message_received",
                    client_id=client_id,
                    message_type=message_type,
                )

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
                            "payload": {
                                "message": f"Unknown message type: {message_type}"
                            },
                        },
                        client_id,
                    )

            except WebSocketDisconnect:
                disconnect_reason = "client_disconnected"
                break
            except RuntimeError as runtime_error:
                message = str(runtime_error).lower()
                disconnect_error = "disconnect message" in message
                receive_after_disconnect = (
                    "receive" in message and "disconnect" in message
                )

                if disconnect_error or receive_after_disconnect:
                    # Treat as clean disconnect without bubbling an exception to uvicorn
                    disconnect_reason = "client_runtime_disconnect"
                    logger.info(
                        "websocket_receive_after_disconnect",
                        client_id=client_id,
                        error=str(runtime_error),
                    )
                    break

                raise
            except ValidationError as e:
                logger.error("validation_error", client_id=client_id, error=str(e))
                await connection_manager.send_personal_message(
                    {
                        "type": "error",
                        "payload": {
                            "message": "Invalid message format",
                            "details": str(e),
                        },
                    },
                    client_id,
                )
            except Exception as e:
                logger.error(
                    "message_processing_error",
                    client_id=client_id,
                    error=str(e),
                )
                await connection_manager.send_personal_message(
                    {
                        "type": "error",
                        "payload": {
                            "message": "Internal server error",
                            "details": str(e),
                        },
                    },
                    client_id,
                )

    except Exception as e:
        logger.error("websocket_error", client_id=client_id, error=str(e))
        disconnect_reason = "server_error"
    finally:
        if connected:
            logger.info(
                "client_disconnected",
                client_id=client_id,
                reason=disconnect_reason,
            )
            await connection_manager.disconnect(client_id)


async def handle_task_request(client_id: str, payload: Dict):
    """Handle task request from client"""
    try:
        request_payload = TaskRequestPayload(**payload)
        logger.info(
            "task_processing",
            task_id=request_payload.id,
            task_type=request_payload.type,
            client_id=client_id,
        )

        await connection_manager.send_personal_message(
            {
                "type": "task_acknowledged",
                "payload": TaskAcceptedPayload(task_id=request_payload.id).model_dump(),
            },
            client_id,
        )

        if container is None:
            logger.error("orchestrator_unavailable", client_id=client_id)
            await connection_manager.send_personal_message(
                {
                    "type": "error",
                    "payload": {
                        "message": "Task orchestrator unavailable",
                        "details": "Service container not initialized",
                    },
                },
                client_id,
            )
        else:
            orchestrator = container.task_orchestrator()
            result: TaskSessionResult = await orchestrator.execute(request_payload)

            await connection_manager.send_personal_message(
                {
                    "type": "agent_response",
                    "payload": result.model_dump(),
                },
                client_id,
            )

    except ValidationError as e:
        logger.error("invalid_task_payload", client_id=client_id, error=str(e))
        await connection_manager.send_personal_message(
            {
                "type": "error",
                "payload": {
                    "message": "Invalid task format",
                    "details": str(e),
                },
            },
            client_id,
        )


async def handle_ping(client_id: str):
    """Handle ping message"""
    await connection_manager.send_personal_message(
        {"type": "pong", "payload": {"timestamp": asyncio.get_event_loop().time()}},
        client_id,
    )


async def handle_mode_change(client_id: str, payload: Dict):
    """Handle mode change request (offline/online)"""
    mode = payload.get("mode", "offline")
    logger.info("mode_changed", client_id=client_id, mode=mode)

    await connection_manager.send_personal_message(
        {
            "type": "mode_changed",
            "payload": {
                "mode": mode,
                "message": f"Mode changed to {mode}",
                "timestamp": asyncio.get_event_loop().time(),
            },
        },
        client_id,
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("server_starting", creator="Herman Swanepoel")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


# Add rate limiting middleware after app initialization
# Note: This needs to be done after rate_limiter is initialized in lifespan
@app.on_event("startup")
async def configure_rate_limiting():
    if container is None:
        logger.warning("rate_limiter_unavailable", reason="container_not_initialized")
        return

    limiter = container.rate_limiter()
    if limiter._enabled:
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter, enabled=True)
