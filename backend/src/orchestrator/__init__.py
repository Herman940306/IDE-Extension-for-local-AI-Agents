"""
Orchestrator module for meta-controller and task routing
Project Creator: Herman Swanepoel
"""

from .cognitive_trace import CognitiveTraceStore
from .dual_process_integration import (
    DualProcessSystem,
    close_dual_process_system,
    get_dual_process_system,
)
from .meta_controller import MetaController
from .reasoning_coordinator import ProcessingMode, ReasoningCoordinator, ReasoningResult
from .task_router import TaskRouter

__all__ = [
    "MetaController",
    "TaskRouter",
    "CognitiveTraceStore",
    "ReasoningCoordinator",
    "ProcessingMode",
    "ReasoningResult",
    "DualProcessSystem",
    "get_dual_process_system",
    "close_dual_process_system",
]
