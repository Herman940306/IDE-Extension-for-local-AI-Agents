"""
Orchestrator module for meta-controller and task routing
Project Creator: Herman Swanepoel
"""

from .meta_controller import MetaController
from .task_router import TaskRouter
from .cognitive_trace import CognitiveTraceStore
from .reasoning_coordinator import ReasoningCoordinator, ProcessingMode, ReasoningResult
from .dual_process_integration import DualProcessSystem, get_dual_process_system, close_dual_process_system

__all__ = [
    "MetaController",
    "TaskRouter",
    "CognitiveTraceStore",
    "ReasoningCoordinator",
    "ProcessingMode",
    "ReasoningResult",
    "DualProcessSystem",
    "get_dual_process_system",
    "close_dual_process_system"
]
