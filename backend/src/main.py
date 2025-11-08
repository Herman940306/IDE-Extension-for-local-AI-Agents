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

import requests
from celery.result import AsyncResult  # type: ignore
from fastapi import (
    BackgroundTasks,
    FastAPI,
    Response,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
)
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
from src.api.middleware import (
    CorrelationIDMiddleware,
    RateLimitMiddleware,
    RequestSizeMiddleware,
)
from src.api.router_endpoints import init_router_endpoints
from src.api.router_endpoints import router as router_api
from src.core.config import get_settings
from src.core.container import Container
from src.core.logging import configure_logging, get_logger

# Imports for debug/config endpoints will be added when endpoints are defined
from src.models.session import (
    TaskAcceptedPayload,
    TaskRequestPayload,
    TaskSessionResult,
)
from src.services.connection_manager import ConnectionManager
from src.services.llm_router import InteractionMode, LLMRouter
from src.services.mode_manager import ModeManager, OperationMode
from src.services.ollama_service import get_ollama_service
from src.worker.celery_app import app as celery_app  # type: ignore
from mcp_server.ide_agents_mcp_server import (
    AgentsMCPConfig as _AgentsMCPConfig,
    AgentsMCPServer as _AgentsMCPServer,
)

# Configure structured logging
settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Global services (bound at runtime in lifespan to preserve test/import behavior)
connection_manager = ConnectionManager()
container: Optional[Container] = None
mode_manager = ModeManager(default_mode=OperationMode.OFFLINE)
llm_router: Optional[LLMRouter] = None

APP_START_TIME = time.time()


def _format_duration(seconds: float) -> str:
    total_seconds = int(max(0, seconds))
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def wait_for_ollama(
    host: Optional[str] = None,
    timeout: float = 30.0,
    interval: float = 2.0,
) -> bool:
    """Poll the Ollama tags endpoint until it responds or the timeout elapses."""

    target_host = (host or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    candidates = [target_host]

    if "localhost" in target_host:
        ipv4_host = target_host.replace("localhost", "127.0.0.1")
        if ipv4_host not in candidates:
            candidates.append(ipv4_host)

    deadline = time.time() + timeout

    while time.time() < deadline:
        for candidate in candidates:
            try:
                response = requests.get(f"{candidate}/api/tags", timeout=3)
                if response.status_code == 200:
                    logger.info("ollama_ready", host=candidate)
                    return True
                logger.debug(
                    "ollama_wait_non_200",
                    host=candidate,
                    status=response.status_code,
                )
            except requests.RequestException as exc:
                logger.debug("ollama_wait_retry", host=candidate, error=str(exc))

        time.sleep(interval)

    logger.warning("ollama_wait_timeout", hosts=candidates, timeout=timeout)
    return False


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
    global container, llm_router, mode_manager, connection_manager

    logger.info("backend_starting", creator="Herman Swanepoel")

    # Wait for Ollama without blocking the event loop; tolerate reload cancellations
    try:
        await asyncio.to_thread(wait_for_ollama, os.getenv("OLLAMA_HOST"))
    except asyncio.CancelledError:  # log for clarity during --reload restarts
        logger.info("startup_cancelled_during_ollama_wait")
        raise

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
    # Bind container-managed singletons to globals to avoid divergent instances
    mode_manager = local_container.mode_manager()
    connection_manager = local_container.connection_manager()
    llm_router = local_container.llm_router()
    # Expose container to the app state for access from routes/middleware if needed
    try:
        app.state.container = local_container  # type: ignore[attr-defined]
    except Exception:
        pass  # Defensive: app.state should exist, but avoid failing startup if not
    logger.info("container_initialized")

    # Initialize router endpoints with dependencies
    init_router_endpoints(
        task_orchestrator=local_container.task_orchestrator(),
        metrics_service=local_container.metrics_service(),
    )
    logger.info("router_endpoints_initialized")

    # Initialize embeddings and kick off background indexing + file watcher hooks
    try:
        embeddings = local_container.embeddings_service()
        await embeddings.initialize()

        workspace_root = settings.workspace.root_path
        # Start initial indexing in the background (non-blocking)

        async def _embed_workspace() -> None:
            try:
                await embeddings.embed_codebase(workspace_root)
                logger.info("initial_codebase_indexing_completed")
            except Exception as e:
                logger.warning("initial_codebase_indexing_failed", error=str(e))

        asyncio.create_task(_embed_workspace())

        # Register file change callback to keep embeddings up-to-date (debounced)
        ctx_mgr = local_container.context_manager()

        _pending_changes: dict[str, str] = {}
        _flush_task: Optional[asyncio.Task] = None
        _debounce_seconds = 0.2

        def _schedule_flush() -> None:
            nonlocal _flush_task
            if _flush_task and not _flush_task.done():
                return

            async def _flush() -> None:
                await asyncio.sleep(_debounce_seconds)
                changes = dict(_pending_changes)
                _pending_changes.clear()
                for rel_path, event_type in changes.items():
                    abs_path = str(Path(workspace_root) / rel_path)
                    try:
                        if event_type == "deleted":
                            await embeddings.delete_file_embedding(abs_path)
                        else:
                            try:
                                content = Path(abs_path).read_text(encoding="utf-8")
                            except Exception:
                                content = ""
                            await embeddings.update_file_embedding(abs_path, content)
                    except Exception as e:
                        logger.debug("embedding_update_failed", error=str(e))

            _flush_task = asyncio.create_task(_flush())

        def _on_change(rel_path: str, event_type: str) -> None:
            # Coalesce multiple events per file; prefer 'deleted' once seen
            prev = _pending_changes.get(rel_path)
            if prev == "deleted":
                pass
            else:
                _pending_changes[rel_path] = event_type
            _schedule_flush()

        ctx_mgr.register_file_change_callback(_on_change)
        logger.info("embedding_indexing_hooks_initialized")
    except Exception as e:
        logger.warning("embedding_indexing_init_failed", error=str(e))

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


@app.get("/debug/rag_trace", tags=["health"])  # lightweight debug snapshot
def get_rag_trace(limit: int = 200) -> Dict[str, Any]:
    try:
        from src.services.retrieval.trace import retrieval_trace_buffer as _buf

        traces = _buf.snapshot(limit=limit)
        return {"count": len(traces), "items": traces}
    except Exception as e:
        return {"error": str(e)}


@app.get("/config/rag", tags=["health"])  # expose effective RAG config
def get_rag_config() -> Dict[str, Any]:
    try:
        rag_cfg = {
            "experimental_rag_v2_enabled": settings.experimental_rag_v2_enabled,
            "hybrid_fusion_enabled": getattr(settings, "hybrid_fusion_enabled", False),
            "fusion_weight_vector": getattr(settings, "fusion_weight_vector", 0.6),
            "fusion_weight_bm25": getattr(settings, "fusion_weight_bm25", 0.4),
            "reranker_model": getattr(settings, "reranker_model", None),
            "relevance_threshold": getattr(settings, "relevance_threshold", 0.5),
            "rag_v2_code_top_k": getattr(settings, "rag_v2_code_top_k", 8),
        }
        return rag_cfg
    except Exception as e:
        return {"error": str(e)}


@app.get("/debug/rag_overview", tags=["health"])  # aggregated retrieval stats
def get_rag_overview(limit: int = 400) -> Dict[str, Any]:
    try:
        from src.services.retrieval.trace import retrieval_trace_buffer as _buf

        items = _buf.snapshot(limit=limit)
        if not items:
            return {"count": 0, "means": {}, "top_files": []}

        def _avg(values: list[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        vec = [float(it.get("vector_score", 0.0)) for it in items]
        lex = [float(it.get("lexical_score", 0.0)) for it in items]
        fus = [float(it.get("fusion_score", 0.0)) for it in items]

        # Aggregate by file
        by_file: dict[str, list[float]] = {}
        for it in items:
            f = str(it.get("file") or "unknown")
            by_file.setdefault(f, []).append(float(it.get("fusion_score", 0.0)))

        top_files = sorted(
            (
                {"file": f, "mean_fusion": _avg(scores), "count": len(scores)}
                for f, scores in by_file.items()
            ),
            key=lambda x: cast(float, x["mean_fusion"]),
            reverse=True,
        )[:20]

        return {
            "count": len(items),
            "means": {
                "vector": round(_avg(vec), 4),
                "lexical": round(_avg(lex), 4),
                "fusion": round(_avg(fus), 4),
            },
            "top_files": top_files,
        }
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


@app.get(
    "/debug/embed",
    tags=["health"],
    response_model=None,
)  # quick live embedding sanity-check
async def debug_embed(sample: str = "def add(a,b): return a+b") -> Dict[str, Any]:
    """Run two checks: direct Ollama embed call and via service/DI.

    Returns both results or error messages without raising to simplify debugging.
    """
    results: Dict[str, Any] = {}

    # 1) Direct Ollama call
    try:
        import httpx  # local import to avoid global dependency at import time
        from src.core.config import get_settings as _get_settings

        _s = _get_settings()
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{_s.embeddings.ollama_url}/api/embeddings",
                json={
                    "model": _s.embeddings.ollama_model_name,
                    "input": sample,
                    "prompt": sample,
                },
            )
            results["direct_status"] = r.status_code
            if r.status_code < 400:
                data = r.json()
                emb = data.get("embedding", [])
                results["direct_len"] = len(emb)
                results["direct_preview"] = emb[:5]
            else:
                # include short body fragment to aid diagnostics
                body = await r.aread()
                results["direct_error"] = f"HTTP {r.status_code}: {body[:240]!r}"
    except Exception as e:  # noqa: BLE001
        results["direct_error"] = str(e)

    # 2) Service/DI call
    try:
        global container
        if container is None:
            results["service_error"] = "container_not_initialized"
        else:
            svc = container.embeddings_service()
            if not getattr(svc, "is_initialized", False):
                await svc.initialize()
            vec = await svc.embed_code(sample)
            model_name = svc.ollama_model_name if svc.provider == "ollama" else svc.model_name
            results.update(
                {
                    "service_provider": svc.provider,
                    "service_model": model_name,
                    "service_len": len(vec),
                    "service_preview": vec[:5],
                }
            )
    except Exception as e:  # noqa: BLE001
        results["service_error"] = str(e)

    return results


@app.get("/debug/rag_overview_page", tags=["health"], response_class=Response)
def rag_overview_page() -> Response:
    """Simple HTML page that fetches /debug/rag_overview and renders it."""
    html = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "  <meta charset='UTF-8'/>\n"
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'/>\n"
        "  <title>RAG Overview</title>\n"
        "  <style>\n"
        "    body{font-family:Segoe UI,Arial,sans-serif;margin:20px;}\n"
        "    table{border-collapse:collapse;}\n"
        "    th,td{border:1px solid #ddd;padding:8px;}\n"
        "    th{background:#f4f6f8;text-align:left;}\n"
        "    code{background:#f2f2f2;padding:2px 4px;border-radius:3px;}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h2>RAG v2 Retrieval Overview</h2>\n"
        "  <p>Raw: <code>/debug/rag_overview</code></p>\n"
        "  <div id='summary'>Loading…</div>\n"
        "  <h3>Top Files by Mean Fusion</h3>\n"
        "  <table id='files'>\n"
        "    <thead><tr><th>File</th><th>Mean Fusion</th><th>Count</th></tr></thead>\n"
        "    <tbody></tbody>\n"
        "  </table>\n"
        "  <script>\n"
        "async function load(){\n"
        "  try{\n"
        "    const res = await fetch('/debug/rag_overview');\n"
        "    const data = await res.json();\n"
        "    const s = document.getElementById('summary');\n"
        "    if(data.error){ s.textContent = 'Error: ' + data.error; return; }\n"
        "    const means = data.means || {};\n"
        "    s.innerHTML = '<b>Items:</b> ' + data.count +\n"
        "      ' &nbsp; | &nbsp; <b>Means</b> — Vector: ' + (means.vector ?? 0) +\n"
        "      ', Lexical: ' + (means.lexical ?? 0) + ', Fusion: ' +\n"
        "      (means.fusion ?? 0);\n"
        "    const tbody = document.querySelector('#files tbody');\n"
        "    tbody.innerHTML='';\n"
        "    (data.top_files||[]).forEach(row=>{\n"
        "      const tr = document.createElement('tr');\n"
        "      tr.innerHTML = '<td>' + row.file + '</td><td>' +\n"
        "        Number(row.mean_fusion).toFixed(4) + '</td><td>' +\n"
        "        row.count + '</td>';\n"
        "      tbody.appendChild(tr);\n"
        "    });\n"
        "  }catch(e){\n"
        "    document.getElementById('summary').textContent = 'Error: ' + e;\n"
        "  }\n"
        "}\n"
        "load();\n"
        "setInterval(load, 5000);\n"
        "  </script>\n"
        "</body></html>\n"
    )
    return Response(content=html, media_type="text/html")


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

        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
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

# Retrieval/RAG metrics
RETRIEVAL_DOCS_CONSIDERED = Counter(
    "retrieval_docs_considered_total",
    "Total documents considered in retrieval",
    labelnames=["stage"],
    registry=APP_METRICS_REGISTRY,
)
RETRIEVAL_DOCS_KEPT = Counter(
    "retrieval_docs_kept_total",
    "Total documents kept after reranker/threshold",
    labelnames=["stage"],
    registry=APP_METRICS_REGISTRY,
)
RETRIEVAL_TOPK_MEAN_FUSION_SCORE = Gauge(
    "retrieval_topk_mean_fusion_score",
    "Mean fusion score for top-k kept documents",
    labelnames=["stage"],
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


def _summarize_jobs() -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "total": len(job_store),
        "by_status": {},
    }
    for job in job_store.values():
        status = str(job.get("status", "unknown"))
        status_counts = summary["by_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    return summary


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

        result = long_job_task.delay(  # type: ignore[attr-defined]
            duration=duration,
            job_type=job_type,
        )
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


# --- MCP proxy endpoints (Option A) ---
def _cfg_from_ultra_mode(ultra_mode: str | None) -> _AgentsMCPConfig:
    mode = (ultra_mode or os.getenv("IDE_AGENTS_ULTRA_MODE") or "local").lower()
    enabled = mode != "disabled"
    return _AgentsMCPConfig(
        backend_base_url=os.getenv("IDE_AGENTS_BACKEND_URL", "http://127.0.0.1:8001"),
        request_timeout=float(os.getenv("IDE_AGENTS_REQUEST_TIMEOUT", "30") or 30),
        ultra_enabled=enabled,
        ultra_mock_enabled=(mode == "mock"),
        ultra_local_enabled=(mode == "local"),
        ultra_url=os.getenv("IDE_AGENTS_ULTRA_URL") if mode == "backend" else None,
        ultra_config_path=os.getenv("IDE_AGENTS_ULTRA_CONFIG"),
    )


@app.post(
    "/mcp/github/rank_repos",
    tags=["mcp"],
)  # body: { query, visibility?, limit?, include?, exclude?, top?, ultraMode? }
async def mcp_rank_github_repos(body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = body or {}
    query = payload.get("query")
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=400, detail="Missing required field: query")
    # Build per-request MCP config from ultraMode
    cfg = _cfg_from_ultra_mode(str(payload.get("ultraMode") or ""))
    server = _AgentsMCPServer(cfg)
    # Whitelist arguments expected by tool
    args = {
        k: v
        for k, v in payload.items()
        if k in {"query", "visibility", "limit", "include", "exclude", "top"}
    }
    try:
        result = await server.call_tool("ide_agents_github_rank_repos", args)
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"mcp_rank_repos_failed: {e}")


@app.post(
    "/mcp/github/rank_all",
    tags=["mcp"],
)
# body: { query, visibility?, limit?, state?, include?, exclude?, top?,
#         items_per_repo?, page?, since?, ultraMode? }
async def mcp_rank_github_all(body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = body or {}
    query = payload.get("query")
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=400, detail="Missing required field: query")
    cfg = _cfg_from_ultra_mode(str(payload.get("ultraMode") or ""))
    server = _AgentsMCPServer(cfg)
    args = {
        k: v
        for k, v in payload.items()
        if k
        in {
            "query",
            "visibility",
            "limit",
            "state",
            "include",
            "exclude",
            "top",
            "items_per_repo",
            "page",
            "since",
        }
    }
    try:
        result = await server.call_tool("ide_agents_github_rank_all", args)
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"mcp_rank_all_failed: {e}")


@app.get("/mcp/health", tags=["mcp"])
async def mcp_health() -> dict[str, Any]:
    cfg = _cfg_from_ultra_mode(os.getenv("IDE_AGENTS_ULTRA_MODE"))
    server = _AgentsMCPServer(cfg)
    try:
        res = await server.call_tool("ide_agents_health", {})
        return {"ok": True, **res}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@app.get("/mcp/github/health", tags=["mcp"])  # lightweight GitHub token check
def mcp_github_health() -> dict[str, Any]:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        return {
            "ok": False,
            "token_present": False,
            "token_valid": False,
            "message": "Missing GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN",
        }
    try:
        resp = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=6,
        )
        if resp.status_code == 200:
            payload = resp.json() if hasattr(resp, "json") else {}
            login = None
            try:
                login = (payload or {}).get("login")
            except Exception:
                login = None
            return {
                "ok": True,
                "token_present": True,
                "token_valid": True,
                "login": login,
            }
        else:
            return {
                "ok": False,
                "token_present": True,
                "token_valid": False,
                "status": resp.status_code,
                "message": "GitHub API /user check failed",
            }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "token_present": True,
            "token_valid": False,
            "error": str(e),
        }


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


@app.get("/api/status", tags=["health"])
async def api_status() -> Dict[str, Any]:
    uptime_seconds = time.time() - APP_START_TIME
    issues: list[str] = []

    redis_status: Dict[str, Any] = {"status": "disabled"}
    cache_stats: Dict[str, Any] = {"enabled": False}
    metrics_summary: Dict[str, Any] = {}
    rate_limit_status: Dict[str, Any] = {"enabled": False}

    if container is not None:
        try:
            redis_client = container.redis_client()
            if inspect.isawaitable(redis_client):
                redis_client = await cast(Awaitable[Any], redis_client)

            if redis_client is None:
                redis_status = {"status": "disabled"}
            else:
                try:
                    ping = redis_client.ping()
                    if inspect.isawaitable(ping):
                        await ping
                    redis_status = {"status": "healthy"}
                except Exception as exc:  # noqa: BLE001 - status reporting
                    redis_status = {
                        "status": "unhealthy",
                        "error": str(exc),
                    }
                    issues.append("redis_unhealthy")
        except Exception as exc:  # noqa: BLE001 - status reporting
            redis_status = {
                "status": "error",
                "error": str(exc),
            }
            issues.append("redis_error")

        try:
            cache_service = container.response_cache()
            cache_stats = await cache_service.get_stats()
        except Exception as exc:  # noqa: BLE001 - status reporting
            cache_stats = {"enabled": False, "error": str(exc)}
            issues.append("cache_stats_error")

        try:
            metrics_service = container.metrics_service()
            report = metrics_service.get_performance_report()
            metrics_summary = report.get("summary", {})
        except Exception as exc:  # noqa: BLE001 - status reporting
            metrics_summary = {"error": str(exc)}
            issues.append("metrics_unavailable")

        try:
            limiter = container.rate_limiter()
            rate_limit_status = {
                "enabled": getattr(limiter, "_enabled", False),
                "default_limit": getattr(limiter, "default_limit", None),
                "default_window": getattr(limiter, "default_window", None),
            }
        except Exception as exc:  # noqa: BLE001 - status reporting
            rate_limit_status = {"enabled": False, "error": str(exc)}
            issues.append("rate_limit_error")

    try:
        ollama_service = get_ollama_service()
        ollama_status = ollama_service.get_health_status()
        if not ollama_status.get("available", False):
            issues.append("ollama_unavailable")
    except Exception as exc:  # noqa: BLE001 - status reporting
        ollama_status = {"available": False, "error": str(exc)}
        issues.append("ollama_error")

    mode_info = mode_manager.get_mode_info()
    privacy_info = mode_manager.get_privacy_status()

    llm_status = {
        "router_initialized": llm_router is not None,
        "default_local_model": getattr(llm_router, "default_local_model", None),
        "openai_configured": bool(
            os.environ.get("OPENAI_API_KEY") or getattr(llm_router, "openai_api_key", None)
        ),
        "interaction_modes": [mode.value for mode in InteractionMode],
        "mode": mode_info.get("current_mode"),
    }

    connections_info = {
        "active": connection_manager.get_connection_count(),
    }

    jobs_info = _summarize_jobs()

    openai_status = {
        "configured": llm_status["openai_configured"],
        "cloud_calls_allowed": mode_manager.can_use_cloud_api(),
    }

    overall_status = "ready" if not issues else "degraded"

    return {
        "status": overall_status,
        "issues": issues,
        "timestamp": time.time(),
        "service": {
            "name": settings.app_name,
            "version": settings.version,
            "uptime_seconds": uptime_seconds,
            "uptime_human": _format_duration(uptime_seconds),
        },
        "mode": mode_info,
        "privacy": privacy_info,
        "connections": connections_info,
        "jobs": jobs_info,
        "metrics": metrics_summary,
        "cache": cache_stats,
        "rate_limit": rate_limit_status,
        "dependencies": {
            "redis": redis_status,
            "ollama": ollama_status,
            "openai": openai_status,
        },
    }


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

    logger.info(
        "mode_changed",
        client_id=client_id,
        mode=result["mode"],
        changed=result["changed"],
    )

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
