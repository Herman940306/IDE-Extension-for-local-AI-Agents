"""
API v2 Routes for Next-Gen features
Project Creator: Herman Swanepoel
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.orchestrator.cognitive_trace import CognitiveTraceStore
from src.orchestrator.meta_controller import MetaController
from src.orchestrator.task_router import TaskRouter
from src.verifier.ensemble import VerifierEnsemble
from src.verifier.provenance_store import ProvenanceStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["v2"])

# Initialize components (singleton pattern)
meta_controller = MetaController()
task_router = TaskRouter()
cognitive_trace_store = CognitiveTraceStore()
verifier_ensemble = VerifierEnsemble()
provenance_store = ProvenanceStore()
dual_process_system = None  # Lazy initialization


# Request/Response Models
class RouteRequest(BaseModel):
    task_type: str
    description: str
    code_context: Optional[str] = None
    language: Optional[str] = None


class RouteResponse(BaseModel):
    intent: str
    complexity: float
    agent_path: List[str]
    requires_verification: bool


class VerifyRequest(BaseModel):
    code: str
    language: str
    context: str
    original_task: Optional[str] = None


class VerifyResponse(BaseModel):
    valid: bool
    confidence: float
    reason: str
    details: Dict[str, Any]


class TraceRequest(BaseModel):
    trace_id: Optional[str] = None
    agent: Optional[str] = None
    limit: int = 100


class TraceResponse(BaseModel):
    traces: List[Dict[str, Any]]
    summary: Optional[str] = None


# Endpoints
@router.post("/route", response_model=RouteResponse)
async def route_task(request: RouteRequest):
    """
    Route a task through the meta-controller.

    Analyzes task intent and complexity, then determines
    the optimal agent execution path.
    """
    try:
        # Analyze task
        analysis = task_router.analyze_task(
            description=request.description,
            code_context=request.code_context,
            language=request.language,
        )

        # Get routing path
        agent_path = meta_controller.route(
            task_type=analysis["intent"], complexity=analysis["complexity"]
        )

        logger.info(f"Routed task: {analysis['intent']} -> {agent_path}")

        return RouteResponse(
            intent=analysis["intent"],
            complexity=analysis["complexity"],
            agent_path=agent_path,
            requires_verification=analysis["requires_verification"],
        )
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify", response_model=VerifyResponse)
async def verify_code(request: VerifyRequest):
    """
    Verify code using the verifier ensemble.

    Runs AST syntax checking and semantic validation
    to ensure code correctness.
    """
    try:
        result = verifier_ensemble.verify(
            code=request.code,
            language=request.language,
            context=request.context,
            original_task=request.original_task,
        )

        logger.info(f"Verification: valid={result['valid']}, conf={result['confidence']:.2f}")

        return VerifyResponse(**result)
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traces", response_model=TraceResponse)
async def get_traces(request: TraceRequest):
    """
    Retrieve cognitive traces for explainability.

    Returns reasoning chains and thought processes
    from agent executions.
    """
    try:
        traces = cognitive_trace_store.get_traces(
            agent=request.agent, trace_id=request.trace_id, limit=request.limit
        )

        # Generate summary if requested
        summary = None
        if traces and request.trace_id:
            summary = cognitive_trace_store.summarize(traces)

        logger.info(f"Retrieved {len(traces)} traces")

        return TraceResponse(traces=traces, summary=summary)
    except Exception as e:
        logger.error(f"Trace retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/state")
async def get_graph_state():
    """
    Get current meta-controller graph state.

    Returns nodes, edges, and performance statistics
    for visualization and debugging.
    """
    try:
        state = meta_controller.get_graph_state()
        logger.info("Retrieved graph state")
        return state
    except Exception as e:
        logger.error(f"Failed to get graph state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/reset")
async def reset_graph():
    """
    Reset meta-controller graph to default state.

    Clears all performance history and resets edge weights.
    """
    try:
        meta_controller.reset_graph()
        logger.info("Reset graph to default state")
        return {"status": "success", "message": "Graph reset complete"}
    except Exception as e:
        logger.error(f"Failed to reset graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/provenance/stats")
async def get_provenance_stats():
    """
    Get provenance statistics.

    Returns aggregate statistics about logged inferences.
    """
    try:
        stats = provenance_store.get_statistics()
        logger.info("Retrieved provenance statistics")
        return stats
    except Exception as e:
        logger.error(f"Failed to get provenance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint for v2 API.

    Returns status of all v2 components.
    """
    return {
        "status": "healthy",
        "version": "2.0",
        "components": {
            "meta_controller": "operational",
            "task_router": "operational",
            "cognitive_traces": "operational",
            "verifier": "operational",
            "provenance": "operational",
        },
    }
