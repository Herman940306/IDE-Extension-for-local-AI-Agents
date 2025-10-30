"""
LLM Router Service - Routes requests between Local (Ollama) and Cloud (OpenAI/Anthropic)
Project Creator: Herman Swanepoel
"""

import os
from enum import Enum
from typing import Any, Dict, Optional

from src.core.logging import get_logger
from src.services.mode_manager import ModeManager, OperationMode
from src.services.ollama_service import OllamaService

logger = get_logger(__name__)


class InteractionMode(str, Enum):
    """Different interaction modes for the AI"""

    CHAT = "chat"
    AGENT = "agent"
    EDIT = "edit"


class LLMRouter:
    """Routes LLM requests to appropriate provider based on mode"""

    def __init__(
        self,
        mode_manager: ModeManager,
        ollama_service: OllamaService,
        openai_api_key: Optional[str] = None,
        default_local_model: Optional[str] = None,
    ):
        self.mode_manager = mode_manager
        self.ollama_service = ollama_service
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.default_local_model = default_local_model

        # System prompts for different modes
        self.system_prompts = {
            InteractionMode.CHAT: (
                "You are AuraIA, a helpful and friendly AI assistant. "
                "Provide clear, conversational responses to user questions. "
                "Be concise but thorough."
            ),
            InteractionMode.AGENT: (
                "You are AuraIA Code Agent, an expert coding assistant. "
                "Generate complete, production-ready code with best practices. "
                "Include comments, error handling, and type hints. "
                "Explain your code decisions briefly."
            ),
            InteractionMode.EDIT: (
                "You are AuraIA Code Editor, specialized in refactoring and "
                "improving existing code. Analyze the code, suggest improvements, "
                "fix bugs, and optimize performance. Explain what you changed and why."
            ),
        }

        logger.info(
            "llm_router_initialized",
            has_ollama=ollama_service.is_available,
            has_openai=openai_api_key is not None,
        )

    async def generate_response(
        self,
        prompt: str,
        interaction_mode: InteractionMode = InteractionMode.CHAT,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response using appropriate LLM based on current mode.

        Args:
            prompt: User's input prompt
            interaction_mode: Chat, Agent, or Edit mode
            context: Additional context (files, previous messages, etc.)

        Returns:
            Response dictionary with content and metadata
        """
        current_mode = self.mode_manager.get_current_mode()

        logger.info(
            "llm_request",
            operation_mode=current_mode.value,
            interaction_mode=interaction_mode.value,
            prompt_length=len(prompt),
        )

        # Build full prompt with system message
        system_prompt = self.system_prompts[interaction_mode]

        if current_mode == OperationMode.OFFLINE:
            return await self._generate_local(prompt, system_prompt, interaction_mode, context)
        else:
            return await self._generate_cloud(prompt, system_prompt, interaction_mode, context)

    async def _generate_local(
        self,
        prompt: str,
        system_prompt: str,
        interaction_mode: InteractionMode,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate response using local Ollama"""

        if not self.ollama_service.is_available:
            logger.warning("ollama_unavailable", fallback="mock_response")
            return {
                "content": self._get_mock_response(interaction_mode, prompt),
                "provider": "mock",
                "model": "none",
                "mode": "offline",
                "interaction_mode": interaction_mode.value,
            }

        try:
            model = self._choose_local_model()

            # Combine system prompt and user prompt
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"

            response = await self.ollama_service.query_ollama_async(
                model=model,
                prompt=full_prompt,
                options={
                    "temperature": 0.7,
                    "num_predict": 2000,
                },
            )

            return {
                "content": response.get("response", ""),
                "provider": "ollama",
                "model": model,
                "mode": "offline",
                "interaction_mode": interaction_mode.value,
                "metadata": {
                    "tokens": response.get("eval_count", 0),
                    "duration_ms": response.get("total_duration", 0) / 1_000_000,
                },
            }

        except Exception as e:
            logger.error("ollama_generation_failed", error=str(e), exc_info=True)
            return {
                "content": f"Error generating local response: {str(e)}",
                "provider": "error",
                "model": "none",
                "mode": "offline",
                "interaction_mode": interaction_mode.value,
            }

    async def _generate_cloud(
        self,
        prompt: str,
        system_prompt: str,
        interaction_mode: InteractionMode,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate response using cloud provider (OpenAI/Anthropic)"""

        if not self.openai_api_key:
            logger.warning("cloud_api_unavailable", reason="no_api_key")
            return {
                "content": (
                    "☁️ Cloud mode is enabled but no API key is configured. "
                    "Please set OPENAI_API_KEY environment variable or switch to Local mode."
                ),
                "provider": "none",
                "model": "none",
                "mode": "online",
                "interaction_mode": interaction_mode.value,
            }

        try:
            # Try OpenAI first
            return await self._generate_openai(prompt, system_prompt, interaction_mode)

        except Exception as e:
            logger.error("cloud_generation_failed", error=str(e), exc_info=True)
            return {
                "content": f"☁️ Cloud API error: {str(e)}. Try switching to Local mode.",
                "provider": "error",
                "model": "none",
                "mode": "online",
                "interaction_mode": interaction_mode.value,
            }

    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: str,
        interaction_mode: InteractionMode,
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API"""

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.openai_api_key)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # balanced price/perf, great default
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )

            content = response.choices[0].message.content if response.choices else ""
            usage = response.usage

            return {
                "content": content,
                "provider": "openai",
                "model": response.model,
                "mode": "online",
                "interaction_mode": interaction_mode.value,
                "metadata": {
                    "tokens": usage.total_tokens if usage else 0,
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                },
            }

        except (ImportError, Exception) as e:
            logger.error("openai_not_installed")
            return {
                "content": "☁️ OpenAI library not installed. Run: pip install openai",
                "provider": "error",
                "model": "none",
                "mode": "online",
                "interaction_mode": interaction_mode.value,
            }

    def _get_mock_response(self, interaction_mode: InteractionMode, prompt: str) -> str:
        """Generate mock response for testing when no LLM is available"""

        responses = {
            InteractionMode.CHAT: (
                f"💬 [Mock Response - Chat Mode]\n\n"
                f"I received your message: '{prompt[:100]}...'\n\n"
                f"This is a mock response because no LLM is currently available. "
                f"To get real responses:\n"
                f"• Local Mode: Ensure Ollama is running with models installed\n"
                f"• Cloud Mode: Set OPENAI_API_KEY environment variable"
            ),
            InteractionMode.AGENT: (
                f"🤖 [Mock Response - Agent Mode]\n\n"
                f"```python\n"
                f"# Generated code for: {prompt[:50]}...\n"
                f"def solution():\n"
                f"    # TODO: Implement actual logic\n"
                f"    pass\n"
                f"```\n\n"
                f"This is mock code. Configure Ollama or OpenAI for real code generation."
            ),
            InteractionMode.EDIT: (
                f"✏️ [Mock Response - Edit Mode]\n\n"
                f"**Analysis:** Your code request: '{prompt[:100]}...'\n\n"
                f"**Suggested Changes:**\n"
                f"• This is a mock refactoring suggestion\n"
                f"• Configure Ollama or OpenAI for real code analysis\n\n"
                f"**Improved Code:**\n"
                f"```python\n"
                f"# Refactored code would appear here\n"
                f"```"
            ),
        }

        return responses.get(interaction_mode, "Mock response")

    def _choose_local_model(self) -> str:
        """Select the most appropriate local model for generation."""

        available_models = self.ollama_service.models

        if self.default_local_model:
            if self.default_local_model in available_models:
                return self.default_local_model

            # Allow using short names without tag suffix if there is an exact match ignoring suffixes
            for candidate in available_models:
                if candidate.startswith(self.default_local_model):
                    logger.info(
                        "llm_router_local_model_match",
                        requested=self.default_local_model,
                        selected=candidate,
                    )
                    return candidate

            logger.warning(
                "llm_router_local_model_unavailable",
                requested=self.default_local_model,
                available=available_models,
            )

        if available_models:
            return available_models[0]

        logger.warning("llm_router_no_local_models")
        return "llama2"
