"""
Enterprise AI Agents Integration - Backend Service
Project Creator: Herman Swanepoel
"""

import asyncio
import inspect
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Awaitable, Dict, Optional, cast

from celery.result import AsyncResult  # type: ignore
from fastapi import BackgroundTasks, FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import ValidationError
from src.api.exception_handlers import register_exception_handlers
from src.api.middleware import CorrelationIDMiddleware, RateLimitMiddleware, RequestSizeMiddleware
from src.api.router_endpoints import init_router_endpoints
from src.api.router_endpoints import router as router_api
from src.core.config import get_settings
from src.core.container import Container
from src.core.logging import configure_logging, get_logger
from src.models.session import TaskAcceptedPayload, TaskRequestPayload, TaskSessionResult
from src.services.connection_manager import ConnectionManager
from src.services.llm_router import InteractionMode, LLMRouter
from src.services.mode_manager import ModeManager, OperationMode
from src.services.ollama_service import get_ollama_service
from src.worker.celery_app import app as celery_app  # type: ignore

# Configure structured logging
settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Global services
connection_manager = ConnectionManager()
container: Optional[Container] = None
mode_manager = ModeManager(default_mode=OperationMode.OFFLINE)
llm_router: Optional[LLMRouter] = None


def _load_openai_key_from_secure_folder() -> None:
    """Load OPENAI_API_KEY from a local, git-ignored secure folder if not set.

    Looks for a file named 'openai.key' in the workspace root folder:
    '<repo_root>/AuraIA IDE Vision and Roadmap/openai.key'.
    Only sets the environment variable if it isn't already set.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return

    try:
        # backend/src/main.py -> parents[0]=backend/src, [1]=backend, [2]=repo root
        repo_root = Path(__file__).resolve().parents[2]
        key_path = repo_root / "AuraIA IDE Vision and Roadmap" / "openai.key"

        if not key_path.exists():
            return

        key_text = key_path.read_text(encoding="utf-8").strip()
        if not key_text:
            logger.warning("openai_key_file_empty", path=str(key_path))
            return

        # Use first non-empty line
        first_line = next((ln.strip() for ln in key_text.splitlines() if ln.strip()), "")
        if first_line.startswith("sk-"):
            os.environ["OPENAI_API_KEY"] = first_line
            logger.info("openai_api_key_loaded", source="secure_folder")
        else:
            logger.warning("openai_key_invalid_format", prefix=first_line[:5])
    except Exception as e:
        # Best-effort; don't crash startup if reading fails
        logger.warning("openai_key_load_failed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global container, llm_router

    logger.info("backend_starting", creator="Herman Swanepoel")

    # Initialize Ollama service
    ollama_service = get_ollama_service()
    if ollama_service.ensure_ollama():
        logger.info(
            "ollama_connected",
            version=ollama_service.version,
            models=len(ollama_service.models),
        )
    else:
        logger.warning(
            "ollama_unavailable",
            message="Ollama service not detected. AI features may be limited.",
        )

    # Initialize DI container
    # Load OpenAI key from secure local folder before wiring the container
    _load_openai_key_from_secure_folder()
    local_container = Container()
    container = local_container
    llm_router = local_container.llm_router()
    logger.info("container_initialized")

    # Initialize router endpoints with dependencies
    init_router_endpoints(
        task_orchestrator=local_container.task_orchestrator(),
        metrics_service=local_container.metrics_service(),
    )
    logger.info("router_endpoints_initialized")

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


@app.get("/health/openai", tags=["health"])  # simple diagnostics; no secrets leaked
def openai_health() -> Dict[str, Any]:
    """Check OpenAI availability and model access.

    - Verifies OPENAI_API_KEY is present (but never returns it)
    - Attempts to retrieve the configured model (gpt-4o-mini) metadata
    """
    key_present = bool(os.environ.get("OPENAI_API_KEY"))
    if not key_present:
        return {
            "provider": "openai",
            "available": False,
            "reason": "no_api_key",
        }

    try:
        import openai  # type: ignore

        client = getattr(openai, "OpenAI")(api_key=os.environ.get("OPENAI_API_KEY"))
        model_id = "gpt-4o-mini"
        model = client.models.retrieve(model_id)

        # model is a pydantic object; extract id safely
        model_id_resolved = getattr(model, "id", model_id)

        return {
            "provider": "openai",
            "available": True,
            "model": model_id_resolved,
            "mode": "online",
        }
    except Exception as e:  # noqa: BLE001 - expose for diagnostics only
        logger.warning("openai_health_failed", error=str(e))
        return {
            "provider": "openai",
            "available": False,
            "error": str(e),
        }


# Add custom middleware (order matters: first added = last executed)
# 1. Correlation ID (first to execute, adds ID to all requests)
app.add_middleware(CorrelationIDMiddleware)

# 2. Request Size Validation (check size before processing)
app.add_middleware(RequestSizeMiddleware, max_size=settings.max_request_size)

# Register router endpoints
app.include_router(router_api)
logger.info("router_endpoints_registered")


# --- Prometheus metrics ---
# Use an app-specific registry to avoid duplicate registration in test runs
APP_METRICS_REGISTRY = CollectorRegistry()
# Basic HTTP metrics: request counts and durations by method/path/status
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status_code"],
    registry=APP_METRICS_REGISTRY,
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "path", "status_code"],
    buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10),
    registry=APP_METRICS_REGISTRY,
)

# Job metrics
JOBS_QUEUED_TOTAL = Counter(
    "jobs_queued_total",
    "Total jobs enqueued",
    labelnames=["job_type"],
    registry=APP_METRICS_REGISTRY,
)
JOBS_COMPLETED_TOTAL = Counter(
    "jobs_completed_total",
    "Total jobs completed by outcome",
    labelnames=["job_type", "outcome"],
    registry=APP_METRICS_REGISTRY,
)
JOBS_IN_PROGRESS = Gauge(
    "jobs_in_progress",
    "Current in-progress jobs",
    labelnames=["job_type"],
    registry=APP_METRICS_REGISTRY,
)
JOB_DURATION_SECONDS = Histogram(
    "job_duration_seconds",
    "Duration of background jobs in seconds",
    labelnames=["job_type", "outcome"],
    buckets=(0.5, 1, 2, 5, 10, 20, 60),
    registry=APP_METRICS_REGISTRY,
)

# Simple in-memory job store
job_store: Dict[str, Dict[str, Any]] = {}
job_lock = asyncio.Lock()


async def _run_long_job(job_id: str, job_type: str, duration: float) -> None:
    """Simulate a long-running job and record metrics/status."""
    start = time.perf_counter()
    JOBS_IN_PROGRESS.labels(job_type=job_type).inc()
    try:
        await asyncio.sleep(duration)
        total = time.perf_counter() - start
        async with job_lock:
            job = job_store.get(job_id)
            if job is not None:
                job["status"] = "completed"
                job["completed_at"] = asyncio.get_event_loop().time()
                job["duration"] = total
        JOBS_COMPLETED_TOTAL.labels(job_type=job_type, outcome="success").inc()
        JOB_DURATION_SECONDS.labels(job_type=job_type, outcome="success").observe(total)
    except Exception as e:  # pragma: no cover - defensive
        total = time.perf_counter() - start
        async with job_lock:
            job = job_store.get(job_id)
            if job is not None:
                job["status"] = "failed"
                job["error"] = str(e)
                job["completed_at"] = asyncio.get_event_loop().time()
                job["duration"] = total
        JOBS_COMPLETED_TOTAL.labels(job_type=job_type, outcome="error").inc()
        JOB_DURATION_SECONDS.labels(job_type=job_type, outcome="error").observe(total)
    finally:
        JOBS_IN_PROGRESS.labels(job_type=job_type).dec()


@app.post("/jobs/long", tags=["jobs"], status_code=202)
async def create_long_job(
    background: BackgroundTasks,
    body: Dict[str, Any] | None = None,
):
    """Enqueue a simulated long-running job using BackgroundTasks.

    body: {"duration_seconds": float (1-15), "job_type": str}
    """
    payload = body or {}
    raw_duration = float(payload.get("duration_seconds", 5.0))
    duration = max(1.0, min(raw_duration, 15.0))
    job_type = str(payload.get("job_type", "long"))

    JOBS_QUEUED_TOTAL.labels(job_type=job_type).inc()
    if settings.use_celery:
        # Enqueue Celery task
        # Local import to avoid startup overhead when Celery is disabled
        from src.worker.celery_app import long_job_task

        result = long_job_task.delay(duration=duration, job_type=job_type)
        return {"job_id": result.id, "status": "queued", "engine": "celery"}
    else:
        # In-process background task
        job_id = str(uuid.uuid4())
        now = asyncio.get_event_loop().time()
        async with job_lock:
            job_store[job_id] = {
                "status": "queued",
                "job_type": job_type,
                "enqueued_at": now,
                "duration": None,
            }
        background.add_task(_run_long_job, job_id, job_type, duration)
        return {"job_id": job_id, "status": "queued", "engine": "background"}


@app.get("/jobs/status/{job_id}", tags=["jobs"])
async def get_job_status(job_id: str):
    if settings.use_celery:
        # Query Celery result backend
        result = AsyncResult(job_id, app=celery_app)
        state = result.state  # PENDING | STARTED | SUCCESS | FAILURE | RETRY | REVOKED
        if state == "PENDING":
            status = "queued"
        elif state == "STARTED":
            status = "in_progress"
        elif state == "SUCCESS":
            status = "completed"
        elif state == "FAILURE":
            status = "failed"
        else:
            status = state.lower()

        info = result.info if isinstance(result.info, dict) else {"raw": str(result.info)}
        return {"job_id": job_id, "status": status, **info}
    else:
        async with job_lock:
            job = job_store.get(job_id)
            if job is None:
                return {"job_id": job_id, "status": "not_found"}
            return {"job_id": job_id, **job}


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
    return Response(generate_latest(APP_METRICS_REGISTRY), media_type=CONTENT_TYPE_LATEST)


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
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "service": "backend",
        "connections": connection_manager.get_connection_count(),
        "components": {},
    }
    components = cast(Dict[str, Any], health_status["components"])

    if container is None:
        components["redis"] = "disabled"
        components["cache"] = {"enabled": False}
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
                components["redis"] = "healthy"
            except Exception:
                components["redis"] = "unhealthy"
                health_status["status"] = "degraded"
        else:
            components["redis"] = "disabled"
    except Exception:
        components["redis"] = "disabled"

    try:
        cache_stats = await container.response_cache().get_stats()
        components["cache"] = cache_stats
    except Exception:
        components["cache"] = {"enabled": False}

    # Check Ollama service status
    try:
        ollama_service = get_ollama_service()
        components["ollama"] = ollama_service.get_health_status()
    except Exception as e:
        components["ollama"] = {"available": False, "error": str(e)}
        health_status["status"] = "degraded"

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
                            "payload": {"message": f"Unknown message type: {message_type}"},
                        },
                        client_id,
                    )

            except WebSocketDisconnect:
                disconnect_reason = "client_disconnected"
                break
            except RuntimeError as runtime_error:
                message = str(runtime_error).lower()
                disconnect_error = "disconnect message" in message
                receive_after_disconnect = "receive" in message and "disconnect" in message

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

        if llm_router is None:
            logger.error("llm_router_unavailable", client_id=client_id)
            await connection_manager.send_personal_message(
                {
                    "type": "error",
                    "payload": {
                        "message": "LLM Router unavailable",
                        "details": "Service container not initialized",
                    },
                },
                client_id,
            )
        else:
            # Extract interaction mode from context metadata (default to CHAT)
            # Check both context.metadata and context dict directly
            if hasattr(request_payload.context, "metadata"):
                mode_str = request_payload.context.metadata.get("interaction_mode", "chat")
            elif isinstance(request_payload.context, dict):
                mode_str = request_payload.context.get("interaction_mode", "chat")
            else:
                mode_str = "chat"

            mode_str = str(mode_str).upper()
            try:
                interaction_mode = InteractionMode[mode_str]
            except KeyError:
                logger.warning(f"Unknown interaction mode: {mode_str}, defaulting to CHAT")
                interaction_mode = InteractionMode.CHAT

            # Generate response using LLM router
            prompt = request_payload.content or request_payload.description

            # Convert context to dict (handle both FieldInfo and TaskContextPayload)
            if hasattr(request_payload.context, "model_dump"):
                context_dict = request_payload.context.model_dump()
            elif isinstance(request_payload.context, dict):
                context_dict = request_payload.context
            else:
                context_dict = {}

            response_data = await llm_router.generate_response(
                prompt=prompt,
                interaction_mode=interaction_mode,
                context=context_dict,
            )

            # Extract text from response data
            response_str = response_data.get("content", "No response generated")
            if not isinstance(response_str, str):
                response_str = str(response_str)

            # Create summary (first 100 chars)
            if len(response_str) > 100:
                summary = response_str[0:100] + "..."
            else:
                summary = response_str

            # Build result payload
            result = TaskSessionResult(
                task_id=request_payload.id,
                status="completed",
                summary=summary,
                responses=[],
                metrics={
                    "interaction_mode": interaction_mode.value,
                    "response_length": len(response_str),
                    "full_response": response_str,
                },
            )

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
    mode_str = payload.get("mode", "local").lower()

    # Map frontend terms to backend OperationMode
    if mode_str in ["local", "offline"]:
        target_mode = OperationMode.OFFLINE
    elif mode_str in ["cloud", "online"]:
        target_mode = OperationMode.ONLINE
    else:
        target_mode = OperationMode.OFFLINE

    result = await mode_manager.set_mode(target_mode)

    logger.info("mode_changed", client_id=client_id, mode=result["mode"], changed=result["changed"])

    await connection_manager.send_personal_message(
        {
            "type": "mode_changed",
            "payload": {
                "mode": result["mode"],
                "message": result["message"],
                "timestamp": asyncio.get_event_loop().time(),
            },
        },
        client_id,
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("server_starting", creator="Herman Swanepoel")

    # Use fully qualified module path so it works whether run as module or script
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


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
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter, enabled=True)
