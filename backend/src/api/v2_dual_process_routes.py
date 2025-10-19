"""
API v2 Dual-Process Reasoning Routes
Project Creator: Herman Swanepoel

Endpoints for System 1 (Fast Reasoner) + System 2 (Analytical Verifier) integration.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.orchestrator.dual_process_integration import get_dual_process_system
from src.orchestrator.reasoning_coordinator import ProcessingMode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/reasoning", tags=["v2-reasoning"])


# Request/Response Models
class ReasoningRequest(BaseModel):
    task_type: str
    description: str
    code_context: str
    language: str
    selected_text: Optional[str] = None
    mode: str = "adaptive"  # adaptive, system1_only, dual_process


class ReasoningResponse(BaseModel):
    success: bool
    suggestions: list
    confidence: float
    reasoning: str
    system1_response: Optional[Dict[str, Any]] = None
    system2_response: Optional[Dict[str, Any]] = None
    verification_passed: Optional[bool] = None
    verification_skipped: Optional[bool] = None
    issues: Optional[list] = None
    metadata: Dict[str, Any]


class StatsResponse(BaseModel):
    total_requests: int
    system1_only_count: int
    dual_process_count: int
    escalations: int
    system1_rate: float
    dual_process_rate: float
    escalation_rate: float
    system1_stats: Dict[str, Any]
    system2_stats: Dict[str, Any]
    graph_state: Dict[str, Any]


# Endpoints
@router.post("/process", response_model=ReasoningResponse)
async def process_reasoning(request: ReasoningRequest):
    """
    Process a reasoning request through the dual-process system.

    Modes:
    - adaptive: Automatically choose System 1 only or System 1 + System 2
    - system1_only: Use only System 1 (fast path)
    - dual_process: Always use both System 1 and System 2

    System 1 (Fast Reasoner): LLaMA 3.2 3B - <200ms for simple tasks
    System 2 (Analytical Verifier): Mistral 7B - <2000ms for verification
    """
    try:
        # Get dual-process system
        system = get_dual_process_system()

        # Parse mode
        mode_map = {
            "adaptive": ProcessingMode.ADAPTIVE,
            "system1_only": ProcessingMode.SYSTEM1_ONLY,
            "dual_process": ProcessingMode.DUAL_PROCESS,
        }
        mode = mode_map.get(request.mode.lower(), ProcessingMode.ADAPTIVE)

        # Process request
        result = await system.process(
            task_type=request.task_type,
            description=request.description,
            code_context=request.code_context,
            language=request.language,
            selected_text=request.selected_text,
            mode=mode,
        )

        logger.info(
            f"Reasoning complete: mode={request.mode}, "
            f"latency={result['metadata']['total_latency_ms']:.0f}ms"
        )

        return ReasoningResponse(**result)

    except Exception as e:
        logger.error(f"Reasoning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats", response_model=StatsResponse)
async def get_reasoning_stats():
    """
    Get dual-process system statistics.

    Returns:
    - Request counts and rates
    - System 1 and System 2 performance metrics
    - Meta-controller graph state
    """
    try:
        system = get_dual_process_system()
        stats = system.get_stats()

        logger.info("Retrieved reasoning statistics")
        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/graph")
async def get_reasoning_graph():
    """
    Get meta-controller graph state for reasoning system.

    Returns nodes, edges, and performance metrics for visualization.
    """
    try:
        system = get_dual_process_system()
        graph_state = system.get_graph_state()

        logger.info("Retrieved reasoning graph state")
        return graph_state

    except Exception as e:
        logger.error(f"Failed to get graph: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def health_check():
    """
    Health check for dual-process reasoning system.

    Verifies that System 1 and System 2 are operational.
    """
    try:
        system = get_dual_process_system()
        stats = system.get_stats()

        return {
            "status": "healthy",
            "system1": {"model": stats["system1_stats"]["model"], "operational": True},
            "system2": {"model": stats["system2_stats"]["model"], "operational": True},
            "total_requests": stats["total_requests"],
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
