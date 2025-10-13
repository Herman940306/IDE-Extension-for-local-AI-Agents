"""
Dual-Process Integration Layer - Factory and Utilities
Project Creator: Herman Swanepoel

Provides factory methods and utilities for creating and managing
the dual-process reasoning system (System 1 + System 2).
"""

import logging
from typing import Optional

from ..models.reasoner import FastReasoner
from ..models.verifier import AnalyticalVerifier
from .task_router import TaskRouter
from .meta_controller import MetaController
from .reasoning_coordinator import ReasoningCoordinator, ProcessingMode
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class DualProcessSystem:
    """
    Factory and manager for the dual-process reasoning system.
    
    Provides a high-level interface for creating and managing
    System 1 (Fast Reasoner) and System 2 (Analytical Verifier).
    """
    
    def __init__(
        self,
        ollama_url: Optional[str] = None,
        reasoner_model: Optional[str] = None,
        verifier_model: Optional[str] = None,
        confidence_threshold: float = 0.75,
        complexity_threshold: float = 0.5
    ):
        """
        Initialize dual-process system.
        
        Args:
            ollama_url: Ollama API URL (defaults to settings)
            reasoner_model: System 1 model name (defaults to settings)
            verifier_model: System 2 model name (defaults to settings)
            confidence_threshold: Threshold for System 2 escalation
            complexity_threshold: Threshold for dual-process mode
        """
        settings = get_settings()
        
        self.ollama_url = ollama_url or settings.ollama_base_url
        self.reasoner_model = reasoner_model or settings.reasoner_model
        self.verifier_model = verifier_model or settings.verifier_model
        
        # Initialize components
        self.reasoner = FastReasoner(
            ollama_url=self.ollama_url,
            model=self.reasoner_model,
            timeout=2.0
        )
        
        self.verifier = AnalyticalVerifier(
            ollama_url=self.ollama_url,
            model=self.verifier_model,
            timeout=5.0
        )
        
        self.task_router = TaskRouter()
        self.meta_controller = MetaController()
        
        self.coordinator = ReasoningCoordinator(
            reasoner=self.reasoner,
            verifier=self.verifier,
            task_router=self.task_router,
            meta_controller=self.meta_controller,
            confidence_threshold=confidence_threshold,
            complexity_threshold=complexity_threshold
        )
        
        logger.info(
            f"DualProcessSystem initialized: "
            f"reasoner={self.reasoner_model}, "
            f"verifier={self.verifier_model}"
        )
    
    async def process(
        self,
        task_type: str,
        description: str,
        code_context: str,
        language: str,
        selected_text: Optional[str] = None,
        mode: ProcessingMode = ProcessingMode.ADAPTIVE
    ):
        """
        Process a request through the dual-process system.
        
        Args:
            task_type: Type of task
            description: Task description
            code_context: Code context
            language: Programming language
            selected_text: Optional selected code
            mode: Processing mode
            
        Returns:
            ReasoningResult
        """
        return await self.coordinator.process(
            task_type=task_type,
            description=description,
            code_context=code_context,
            language=language,
            selected_text=selected_text,
            mode=mode
        )
    
    def get_stats(self):
        """Get system statistics"""
        return self.coordinator.get_stats()
    
    def get_graph_state(self):
        """Get meta-controller graph state"""
        return self.meta_controller.get_graph_state()
    
    async def close(self):
        """Close all resources"""
        await self.coordinator.close()
        logger.info("DualProcessSystem closed")


# Global instance (singleton pattern)
_dual_process_system: Optional[DualProcessSystem] = None


def get_dual_process_system() -> DualProcessSystem:
    """
    Get or create the global dual-process system instance.
    
    Returns:
        DualProcessSystem instance
    """
    global _dual_process_system
    
    if _dual_process_system is None:
        _dual_process_system = DualProcessSystem()
        logger.info("Created global DualProcessSystem instance")
    
    return _dual_process_system


async def close_dual_process_system():
    """Close the global dual-process system"""
    global _dual_process_system
    
    if _dual_process_system is not None:
        await _dual_process_system.close()
        _dual_process_system = None
        logger.info("Closed global DualProcessSystem instance")
