"""
Router Endpoints - HTTP API for Multi-Model Routing
Project Creator: Herman Swanepoel

Provides REST API for intelligent model routing, metrics, and auto-tuning.
Endpoints:
- POST /route: Route task to optimal model
- GET /metrics: Get performance metrics
- POST /autotune: Auto-tuning recommendations
- POST /notify: Callback for notifications
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["routing"])


# Request/Response models
class RouteRequest(BaseModel):
    """Request model for task routing"""

    task_type: str
    prompt: str
    context: Optional[str] = None
    use_premium_ux: bool = False


class RouteResponse(BaseModel):
    """Response model for routed tasks"""

    text: str
    verified: bool
    safety: bool
    metadata: dict


class AutoTuneRequest(BaseModel):
    """Request model for auto-tuning"""

    approve: bool = False


class NotificationPayload(BaseModel):
    """Notification payload model"""

    message: str
    model: Optional[str] = None
    avg_latency: Optional[float] = None


# Dependency injection placeholders (will be wired by container)
_task_orchestrator = None
_metrics_service = None


def init_router_endpoints(task_orchestrator, metrics_service):
    """
    Initialize router endpoints with dependencies.

    Args:
        task_orchestrator: Task orchestrator instance
        metrics_service: Metrics service instance
    """
    global _task_orchestrator, _metrics_service
    _task_orchestrator = task_orchestrator
    _metrics_service = metrics_service
    logger.info("Router endpoints initialized")


@router.post("/route", response_model=RouteResponse)
async def route_task(request: RouteRequest, background_tasks: BackgroundTasks):
    """
    Route a task to the optimal model and return the result.

    Args:
        request: Task routing request
        background_tasks: FastAPI background tasks

    Returns:
        Routed task result with metadata
    """
    if not _task_orchestrator:
        raise HTTPException(status_code=503, detail="Task orchestrator not available")

    try:
        # Create task request payload
        import time

        from src.models.session import TaskRequestPayload
        from src.models.task import TaskType

        # Map task_type string to TaskType enum
        task_type_map = {
            "code_generation": TaskType.CODE_GENERATION,
            "bug_fix": TaskType.BUG_FIX,
            "refactor": TaskType.REFACTOR,
            "test_generation": TaskType.TEST_GENERATION,
            "documentation": TaskType.DOCUMENTATION,
            "general": TaskType.GENERAL,
        }

        task_type = task_type_map.get(request.task_type.lower(), TaskType.GENERAL)

        task_payload = TaskRequestPayload(
            id=f"route-{int(time.time() * 1000)}",
            type=task_type,
            description=request.prompt,
            content=request.context or "",
        )

        # Execute task through orchestrator
        start_time = time.time()

        result = await _task_orchestrator.execute_task(task_payload)

        latency = time.time() - start_time

        # Record metrics
        if _metrics_service and result.responses:
            for agent_run in result.responses:
                agent_resp = agent_run.response
                model = (
                    agent_resp.metadata.get("selected_model", "unknown")
                    if agent_resp.metadata
                    else "unknown"
                )
                success = (
                    agent_resp.suggestions is not None
                    and len(agent_resp.suggestions) > 0
                )
                _metrics_service.record_call(
                    model=model, latency=latency, success=success
                )

        # Check for auto-tune recommendations in background
        if _metrics_service:
            background_tasks.add_task(
                _check_autotune_recommendations, request.task_type
            )

        # Format response
        text = ""
        if result.responses and result.responses[0].response.suggestions:
            text = (
                result.responses[0].response.suggestions[0].code
                or "No response generated"
            )

        return RouteResponse(
            text=text,
            verified=result.verification is not None,
            safety=True,  # Will be populated from safety layer
            metadata={
                "latency": latency,
                "models_used": [
                    (
                        r.response.metadata.get("selected_model", "unknown")
                        if r.response.metadata
                        else "unknown"
                    )
                    for r in result.responses
                ],
                "task_type": request.task_type,
            },
        )

    except Exception as e:
        logger.error("Task routing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@router.get("/metrics")
async def get_metrics():
    """
    Get performance metrics for all models.

    Returns:
        Comprehensive performance report
    """
    if not _metrics_service:
        raise HTTPException(status_code=503, detail="Metrics service not available")

    try:
        report = _metrics_service.get_performance_report()
        return report
    except Exception as e:
        logger.error("Failed to get metrics: %s", e)
        raise HTTPException(status_code=500, detail=f"Metrics error: {str(e)}")


@router.get("/metrics/models")
async def get_model_usage():
    """
    Get model usage statistics sorted by call count.

    Returns:
        List of model usage stats
    """
    if not _metrics_service:
        raise HTTPException(status_code=503, detail="Metrics service not available")

    try:
        stats = _metrics_service.get_model_usage_stats()
        return {"models": stats}
    except Exception as e:
        logger.error("Failed to get model usage: %s", e)
        raise HTTPException(status_code=500, detail=f"Model usage error: {str(e)}")


@router.post("/autotune")
async def autotune(request: AutoTuneRequest):
    """
    Get or apply auto-tuning recommendations.

    Args:
        request: Auto-tune request with approval flag

    Returns:
        Auto-tune recommendations or application status
    """
    if not _metrics_service:
        raise HTTPException(status_code=503, detail="Metrics service not available")

    try:
        recommendations = _metrics_service.get_auto_tune_recommendations()

        if request.approve:
            # In a real implementation, this would apply the recommendations
            # by updating model configurations or YAML files
            logger.info(
                "Auto-tune approved: would apply %d recommendations",
                len(recommendations),
            )
            return {
                "status": "accepted",
                "note": (
                    "Auto-tune recommendations would be applied here. "
                    "In production, this updates routing YAML and configs."
                ),
                "recommendations": recommendations,
            }
        else:
            return {
                "status": "preview",
                "recommendations": recommendations,
            }

    except Exception as e:
        logger.error("Auto-tune failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Auto-tune error: {str(e)}")


@router.post("/notify")
async def receive_notification(payload: NotificationPayload):
    """
    Receive notifications from router or external systems.

    Args:
        payload: Notification payload

    Returns:
        Acknowledgment
    """
    logger.info(
        "Received notification: %s (model=%s, latency=%.2f)",
        payload.message,
        payload.model or "N/A",
        payload.avg_latency or 0.0,
    )

    # Could trigger alerts, UI updates, etc.
    return {"ok": True, "received": payload.message}


async def _check_autotune_recommendations(task_type: str):
    """
    Background task to check for auto-tune recommendations.

    Args:
        task_type: Type of task that was executed
    """
    if not _metrics_service:
        return

    try:
        recommendations = _metrics_service.get_auto_tune_recommendations()

        # If we have high-severity recommendations, log them
        high_severity = [r for r in recommendations if r.get("severity") == "high"]

        if high_severity:
            logger.warning(
                "Auto-tune: %d high-severity issues detected after %s task",
                len(high_severity),
                task_type,
            )
            for rec in high_severity[:3]:  # Log first 3
                logger.warning("  - %s: %s", rec["model"], rec["issue"])

    except Exception as e:
        logger.error("Auto-tune check failed: %s", e)
