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
    """Configuration for a specific model"""

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
    ):
        self.name = name
        self.role = role
        self.keep_alive = keep_alive
        self.force_cpu = force_cpu
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.description = description


class MultiModelRouter:
    """
    Routes tasks to appropriate models based on task type, complexity, and resource availability.

    Model Assignment Strategy:
    - 🧠 System 1 (Fast): Qwen3:8B - Top-tier reasoning & coding speed
    - ⚙️ Task Router: Qwen3:4B - Light classification logic
    - 💻 Code Engine: CodeLlama:7B - Reliable code generation
    - 🧩 System 2 Verifier: DeepSeek-R1:8B - Analytical validation
    - 🧩 Fallback: CodeLlama:13B-Instruct-Q4_0 - CPU-safe deep reasoning
    - 💬 UX Premium: Gemma3:12B - Quality conversational responses
    - 💬 UX Light: Gemma3:4B - Quick help prompts
    - 🔍 Embeddings: Nomic-Embed-Text - Semantic search
    - 🛡 Safety: Phi3:mini/medium - Content moderation
    - 🧠 Legacy: LLaMA 3.2:3B - Emergency fallback
    """

    def __init__(self):
        """Initialize the multi-model router with optimized model configurations."""
        self.models = self._initialize_models()
        self.task_to_role_map = self._build_task_routing_map()
        logger.info("Multi-Model Router initialized with 10 specialized models")

    def _initialize_models(self) -> Dict[ModelRole, ModelConfig]:
        """Initialize all model configurations."""
        return {
            # 🧠 System 1 - Fast Reasoner (Primary Intelligence)
            ModelRole.SYSTEM1_FAST: ModelConfig(
                name="qwen3:8b",
                role=ModelRole.SYSTEM1_FAST,
                keep_alive="30m",  # Keep resident for interactive use
                force_cpu=False,
                timeout=30.0,
                temperature=0.7,
                max_tokens=2000,
                description="Top-tier reasoning & coding speed, modern tokenization",
            ),
            # ⚙️ Task Router - Light Classification
            ModelRole.TASK_ROUTER: ModelConfig(
                name="qwen3:4b",
                role=ModelRole.TASK_ROUTER,
                keep_alive="15m",
                force_cpu=False,
                timeout=15.0,
                temperature=0.3,  # Low temp for consistent classification
                max_tokens=500,
                description="Fast logic classifier for task routing",
            ),
            # 💻 Code Engine - Specialized Code Generation
            ModelRole.CODE_ENGINE: ModelConfig(
                name="codellama:7b",
                role=ModelRole.CODE_ENGINE,
                keep_alive="20m",
                force_cpu=False,
                timeout=45.0,
                temperature=0.2,  # Low temp for deterministic code
                max_tokens=4000,
                description="Reliable code generation with stable token handling",
            ),
            # 🧩 System 2 - Deep Verifier
            ModelRole.SYSTEM2_VERIFY: ModelConfig(
                name="deepseek-r1:8b",
                role=ModelRole.SYSTEM2_VERIFY,
                keep_alive="10m",
                force_cpu=False,
                timeout=60.0,
                temperature=0.5,
                max_tokens=3000,
                description="Analytical thinker for logic validation and error tracing",
            ),
            # 🧩 Fallback Reasoner - CPU-Safe Deep Reasoning
            ModelRole.FALLBACK: ModelConfig(
                name="codellama:13b-instruct-q4_0",
                role=ModelRole.FALLBACK,
                keep_alive="0",  # Load on demand
                force_cpu=True,  # CPU-safe for resource constraints
                timeout=90.0,
                temperature=0.7,
                max_tokens=3000,
                description="CPU-safe fallback for deep reasoning when GPU saturated",
            ),
            # 💬 UX Premium - High-Quality Conversational
            ModelRole.UX_PREMIUM: ModelConfig(
                name="gemma3:12b",
                role=ModelRole.UX_PREMIUM,
                keep_alive="10m",
                force_cpu=False,
                timeout=40.0,
                temperature=0.8,  # Higher temp for warmth
                max_tokens=2000,
                description="Premium-quality tone and phrasing for warmth and humanity",
            ),
            # 💬 UX Light - Quick Help
            ModelRole.UX_LIGHT: ModelConfig(
                name="gemma3:4b",
                role=ModelRole.UX_LIGHT,
                keep_alive="15m",
                force_cpu=True,  # CPU-friendly
                timeout=20.0,
                temperature=0.7,
                max_tokens=1000,
                description="Quick help prompts and doc explanations",
            ),
            # 🔍 Embeddings - Context Memory
            ModelRole.EMBEDDINGS: ModelConfig(
                name="nomic-embed-text",
                role=ModelRole.EMBEDDINGS,
                keep_alive="30m",
                force_cpu=True,
                timeout=10.0,
                temperature=0.0,  # Not applicable for embeddings
                max_tokens=0,  # Not applicable
                description="Excellent embeddings for semantic search",
            ),
            # 🛡 Safety Layer - Content Moderation
            ModelRole.SAFETY: ModelConfig(
                name="phi3:mini",
                role=ModelRole.SAFETY,
                keep_alive="-1",  # Always resident
                force_cpu=True,
                timeout=15.0,
                temperature=0.1,  # Very low for consistent safety
                max_tokens=500,
                description="Reliable open moderation for code and NL responses",
            ),
            # 🧠 Legacy Fallback - Emergency Only
            ModelRole.LEGACY: ModelConfig(
                name="llama3.2:3b",
                role=ModelRole.LEGACY,
                keep_alive="5m",
                force_cpu=True,
                timeout=20.0,
                temperature=0.7,
                max_tokens=1500,
                description="Emergency local fallback for resource-limited scenarios",
            ),
        }

    def _build_task_routing_map(self) -> Dict[TaskType, List[ModelRole]]:
        """
        Build task-to-model routing map.
        Returns list of models in priority order (primary, fallback1, fallback2).
        """
        return {
            # Code-related tasks -> Code Engine (primary), System 1 (fallback)
            TaskType.CODE_GENERATION: [
                ModelRole.CODE_ENGINE,
                ModelRole.SYSTEM1_FAST,
                ModelRole.FALLBACK,
            ],
            TaskType.BUG_FIX: [
                ModelRole.CODE_ENGINE,
                ModelRole.SYSTEM1_FAST,
                ModelRole.FALLBACK,
            ],
            TaskType.REFACTORING: [
                ModelRole.CODE_ENGINE,
                ModelRole.SYSTEM1_FAST,
                ModelRole.FALLBACK,
            ],
            # Testing -> System 1 (primary), Code Engine (assist)
            TaskType.TEST_GENERATION: [
                ModelRole.SYSTEM1_FAST,
                ModelRole.CODE_ENGINE,
                ModelRole.FALLBACK,
            ],
            # Documentation -> UX Premium (primary), UX Light (fallback)
            TaskType.DOCUMENTATION: [
                ModelRole.UX_PREMIUM,
                ModelRole.UX_LIGHT,
                ModelRole.SYSTEM1_FAST,
            ],
            # General tasks -> System 1 (primary)
            TaskType.GENERAL: [
                ModelRole.SYSTEM1_FAST,
                ModelRole.UX_PREMIUM,
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
        logger.info(
            f"Routed {task_type.value} task (complexity: {complexity}) to {model_config.name}"
        )
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
