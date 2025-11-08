"""
Multi-Model Router - Intelligent Task-Based Model Selection
Project Creator: Herman Swanepoel

Routes tasks to optimal models based on capabilities and requirements.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List

from src.models.task import TaskType

logger = logging.getLogger(__name__)


class ModelRole(str, Enum):
    """Model roles in the multi-agent system"""

    SYSTEM1_FAST = "system1_fast"  # Fast reasoning
    SYSTEM2_VERIFY = "system2_verify"  # Deep verification
    CODE_ENGINE = "code_engine"  # Code generation
    TASK_ROUTER = "task_router"  # Light classification
    UX_PREMIUM = "ux_premium"  # Conversational quality
    UX_LIGHT = "ux_light"  # Quick help
    EMBEDDINGS = "embeddings"  # Context search
    SAFETY = "safety"  # Content moderation
    FALLBACK = "fallback"  # Resource constraints
    LEGACY = "legacy"  # Emergency fallback


class ModelConfig:
    """Configuration for a specific model with automatic fallbacks"""

    def __init__(
        self,
        name: str,
        role: ModelRole,
        keep_alive: str = "5m",
        force_cpu: bool = False,
        timeout: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        description: str = "",
        fallback_models: List[str] = None,
    ) -> None:
        self.name = name
        self.role = role
        self.keep_alive = keep_alive
        self.fallback_models = fallback_models or []
        self.force_cpu = force_cpu
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.description = description


class MultiModelRouter:
    """
    Routes tasks to appropriate models with automatic fallback.

    Optimized for 1080 Ti (11GB VRAM) + 16GB RAM configuration.
    """

    def __init__(self, show_model_names: bool = False) -> None:
        """
        Initialize the multi-model router.

        Args:
            show_model_names: If True, log model routing details (default: False)
        """
        self.models = self._initialize_models()
        self.task_to_role_map = self._build_task_routing_map()
        self.show_model_names = show_model_names
        logger.info("Multi-Model Router initialized with 10 specialized models")

    def _initialize_models(self) -> Dict[ModelRole, ModelConfig]:
        """
        Initialize model configurations optimized for 1080 Ti (11GB VRAM) + 16GB RAM.

        Strategy:
        - Primary models: Q4 quantization for GPU (qwen3:8b, codellama:7b)
        - Fallbacks: Automatic model selection if primary unavailable
        - Resource management: <10GB VRAM, ~12-13GB RAM total
        """
        return {
            # 🧠 System 1 - Fast Reasoner (Primary Intelligence)
            ModelRole.SYSTEM1_FAST: ModelConfig(
                name="qwen3:8b-q4_K_M",  # Primary (GPU, Q4)
                fallback_models=["llama3.2:3b", "phi3:mini"],  # Auto-fallback
                role=ModelRole.SYSTEM1_FAST,
                keep_alive="30m",
                force_cpu=False,
                timeout=30.0,
                temperature=0.7,
                max_tokens=600,
                description="Fast reasoning",
            ),
            # ⚙️ Task Router - Light Classification
            ModelRole.TASK_ROUTER: ModelConfig(
                name="gemma3:4b",  # Primary (GPU, FP16)
                fallback_models=["phi3:mini", "llama3.2:3b"],
                role=ModelRole.TASK_ROUTER,
                keep_alive="15m",
                force_cpu=False,
                timeout=15.0,
                temperature=0.3,
                max_tokens=500,
                description="Task classification",
            ),
            # 💻 Code Engine - Specialized Code Generation
            ModelRole.CODE_ENGINE: ModelConfig(
                name="codellama:7b-q4_K_M",  # Primary (GPU, Q4)
                fallback_models=["mistral:7b", "llama3.2:3b"],
                role=ModelRole.CODE_ENGINE,
                keep_alive="20m",
                force_cpu=False,
                timeout=45.0,
                temperature=0.2,
                max_tokens=4000,
                description="Code generation",
            ),
            # 🧩 System 2 - Deep Verifier
            ModelRole.SYSTEM2_VERIFY: ModelConfig(
                name="deepseek-r1:8b-q4_K_M",  # Primary (CPU fallback, Q4)
                fallback_models=["mistral:7b", "llama3.2:3b"],
                role=ModelRole.SYSTEM2_VERIFY,
                keep_alive="10m",
                force_cpu=False,  # Try GPU first, CPU if needed
                timeout=60.0,
                temperature=0.5,
                max_tokens=3000,
                description="Logic verification",
            ),
            # 🧩 Fallback Reasoner - General Purpose
            ModelRole.FALLBACK: ModelConfig(
                name="mistral:7b",  # Available fallback
                fallback_models=["llama3.2:3b", "phi3:mini"],
                role=ModelRole.FALLBACK,
                keep_alive="10m",
                force_cpu=False,
                timeout=45.0,
                temperature=0.7,
                max_tokens=2000,
                description="General fallback",
            ),
            # 💬 UX Premium - High-Quality Conversational
            ModelRole.UX_PREMIUM: ModelConfig(
                name="gemma3:4b",  # Primary (GPU, FP16)
                fallback_models=["phi3:mini", "llama3.2:3b"],
                role=ModelRole.UX_PREMIUM,
                keep_alive="15m",
                force_cpu=False,
                timeout=30.0,
                temperature=0.8,
                max_tokens=800,
                description="Conversational",
            ),
            # 💬 UX Light - Quick Help
            ModelRole.UX_LIGHT: ModelConfig(
                name="phi3:mini",  # Primary (CPU, FP16)
                fallback_models=["llama3.2:3b"],
                role=ModelRole.UX_LIGHT,
                keep_alive="15m",
                force_cpu=True,
                timeout=20.0,
                temperature=0.7,
                max_tokens=800,
                description="Quick help",
            ),
            # 🔍 Embeddings - Context Memory
            ModelRole.EMBEDDINGS: ModelConfig(
                name="nomic-embed-text",  # Primary (CPU, FP16)
                fallback_models=[],  # No fallback for embeddings
                role=ModelRole.EMBEDDINGS,
                keep_alive="30m",
                force_cpu=True,
                timeout=10.0,
                temperature=0.0,
                max_tokens=0,
                description="Semantic search",
            ),
            # 🛡 Safety Layer - Content Moderation
            ModelRole.SAFETY: ModelConfig(
                name="phi3:mini",  # Primary (CPU, FP16)
                fallback_models=["llama3.2:3b"],
                role=ModelRole.SAFETY,
                keep_alive="-1",
                force_cpu=True,
                timeout=15.0,
                temperature=0.1,
                max_tokens=500,
                description="Content moderation",
            ),
            # 🧠 Legacy Fallback - Emergency Only
            ModelRole.LEGACY: ModelConfig(
                name="llama3.2:3b",  # Primary (available)
                fallback_models=["phi3:mini"],
                role=ModelRole.LEGACY,
                keep_alive="10m",
                force_cpu=True,
                timeout=20.0,
                temperature=0.7,
                max_tokens=1000,
                description="Emergency fallback",
            ),
        }

    def _build_task_routing_map(self) -> Dict[TaskType, List[ModelRole]]:
        """
        Build task-to-model routing map with focus-based model selection.

        FOCUS MODES:
        - CODE FOCUS (code_gen, bug_fix, refactor): CodeLlama -> Fast, precise code output
        - DEBUG FOCUS (bug_fix): CodeLlama -> Technical bug analysis
        - DOCUMENTATION FOCUS (documentation): CodeLlama -> Concise code explanations
        - TEST FOCUS (test_generation): Qwen3:8B -> Comprehensive test coverage
        - CHAT MODE (general): Qwen3:8B/Gemma3 -> Conversational, contextual responses

        Returns list of models in priority order (primary, fallback1, fallback2).
        """
        return {
            # CODE FOCUS: CodeLlama for focused code generation
            TaskType.CODE_GENERATION: [
                ModelRole.CODE_ENGINE,  # Primary: Direct code output
                ModelRole.SYSTEM1_FAST,
                ModelRole.FALLBACK,
            ],
            # DEBUG FOCUS: CodeLlama for technical debugging
            TaskType.BUG_FIX: [
                ModelRole.CODE_ENGINE,  # Primary: Bug identification + fix
                ModelRole.SYSTEM1_FAST,
                ModelRole.FALLBACK,
            ],
            # REFACTOR FOCUS: CodeLlama for code optimization
            TaskType.REFACTOR: [
                ModelRole.CODE_ENGINE,  # Primary: Technical improvements
                ModelRole.SYSTEM1_FAST,
                ModelRole.FALLBACK,
            ],
            # TEST FOCUS: Qwen3 for comprehensive test design
            TaskType.TEST_GENERATION: [
                ModelRole.SYSTEM1_FAST,  # Primary: Smart test coverage
                ModelRole.CODE_ENGINE,
                ModelRole.FALLBACK,
            ],
            # DOCUMENTATION FOCUS: CodeLlama for concise code explanation
            TaskType.DOCUMENTATION: [
                ModelRole.CODE_ENGINE,  # Primary: Technical, focused explanations
                ModelRole.SYSTEM1_FAST,
                ModelRole.UX_LIGHT,  # Fallback to light UX, not premium
            ],
            # CHAT MODE: Conversational models for general discussion
            TaskType.GENERAL: [
                ModelRole.SYSTEM1_FAST,  # Primary: Context-aware responses
                ModelRole.UX_PREMIUM,  # Secondary: Friendly, detailed conversation
                ModelRole.LEGACY,
            ],
        }

    def route_task(
        self,
        task_type: TaskType,
        use_premium_ux: bool = False,
        complexity: str = "medium",
    ) -> ModelConfig:
        """
        Route a task to the appropriate model based on type and requirements.

        Args:
            task_type: Type of task to perform
            use_premium_ux: Whether to prefer premium UX models for responses
            complexity: Task complexity ("low", "medium", "high")

        Returns:
            ModelConfig for the selected model
        """
        # Get priority list for this task type
        role_priority = self.task_to_role_map.get(
            task_type, [ModelRole.SYSTEM1_FAST, ModelRole.LEGACY]
        )

        # For premium UX requests on documentation/general tasks, prioritize UX models
        if use_premium_ux and task_type in [TaskType.DOCUMENTATION, TaskType.GENERAL]:
            if ModelRole.UX_PREMIUM in role_priority:
                selected_role = ModelRole.UX_PREMIUM
            else:
                selected_role = role_priority[0]
        else:
            # Use primary model from priority list
            selected_role = role_priority[0]

        model_config = self.models[selected_role]

        # Only log routing info if enabled (default: hidden for clean UX)
        if self.show_model_names:
            logger.info(f"Routed {task_type.value} task to {model_config.name}")

        return model_config

    def get_verifier_model(self) -> ModelConfig:
        """Get the verification model (System 2)."""
        return self.models[ModelRole.SYSTEM2_VERIFY]

    def get_embeddings_model(self) -> ModelConfig:
        """Get the embeddings model for semantic search."""
        return self.models[ModelRole.EMBEDDINGS]

    def get_safety_model(self) -> ModelConfig:
        """Get the safety/moderation model."""
        return self.models[ModelRole.SAFETY]

    def get_fallback_chain(self, primary_role: ModelRole) -> List[ModelConfig]:
        """
        Get fallback chain for a given primary role.

        Returns list of models to try in order: [primary, fallback1, fallback2, ...]
        """
        # Define fallback chains
        fallback_chains = {
            ModelRole.SYSTEM1_FAST: [
                ModelRole.SYSTEM1_FAST,
                ModelRole.FALLBACK,
                ModelRole.LEGACY,
            ],
            ModelRole.CODE_ENGINE: [
                ModelRole.CODE_ENGINE,
                ModelRole.FALLBACK,
                ModelRole.SYSTEM1_FAST,
            ],
            ModelRole.SYSTEM2_VERIFY: [
                ModelRole.SYSTEM2_VERIFY,
                ModelRole.FALLBACK,
                ModelRole.SYSTEM1_FAST,
            ],
            ModelRole.UX_PREMIUM: [
                ModelRole.UX_PREMIUM,
                ModelRole.UX_LIGHT,
                ModelRole.SYSTEM1_FAST,
            ],
        }

        chain = fallback_chains.get(
            primary_role, [primary_role, ModelRole.SYSTEM1_FAST, ModelRole.LEGACY]
        )
        return [self.models[role] for role in chain]

    def get_model_info(self) -> Dict[str, Dict]:
        """Get information about all configured models."""
        return {
            role.value: {
                "name": config.name,
                "description": config.description,
                "keep_alive": config.keep_alive,
                "force_cpu": config.force_cpu,
                "timeout": config.timeout,
            }
            for role, config in self.models.items()
        }
