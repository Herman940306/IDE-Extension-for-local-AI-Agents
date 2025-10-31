"""
LLM Service - Unified interface for local and cloud LLM providers
Project Creator: Herman Swanepoel
"""

import os
from typing import Any, Dict, List

from src.core.logging import get_logger
from src.services.mode_manager import ModeManager
from src.services.ollama_service import OllamaService

logger = get_logger(__name__)


class LLMService:
    """
    Unified LLM service that routes requests to local (Ollama) or cloud providers
    based on the current operation mode.
    """

    def __init__(
        self,
        mode_manager: ModeManager,
        ollama_service: OllamaService,
        default_local_model: str = "llama2",
    ):
        """
        Initialize LLM service.

        Args:
            mode_manager: Mode manager instance
            ollama_service: Ollama service instance
            default_local_model: Default Ollama model to use
        """
        self.mode_manager = mode_manager
        self.ollama_service = ollama_service
        self.default_local_model = default_local_model

        # Cloud API configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        logger.info("🤖 LLM Service initialized")
        logger.info(f"   Local: Ollama ({self.ollama_service.is_available})")
        logger.info(
            "   Cloud: OpenAI "
            f"({'✓' if self.openai_api_key else '✗'}), "
            "Anthropic "
            f"({'✓' if self.anthropic_api_key else '✗'})"
        )

    async def generate(
        self,
        prompt: str,
        task_type: str = "chat",
        interaction_mode: str = "chat",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate LLM response based on current mode.

        Args:
            prompt: User prompt/question
            task_type: Type of task (code_generation, documentation, refactor, chat)
            interaction_mode: Interaction mode (agent, chat, edit)
            **kwargs: Additional parameters

        Returns:
            Dictionary with response and metadata
        """
        # Apply mode-specific prompt engineering
        enhanced_prompt = self._enhance_prompt(prompt, task_type, interaction_mode)

        if self.mode_manager.is_offline():
            return await self._generate_local(
                enhanced_prompt, task_type, interaction_mode, **kwargs
            )
        else:
            return await self._generate_cloud(
                enhanced_prompt, task_type, interaction_mode, **kwargs
            )

    def _enhance_prompt(self, prompt: str, task_type: str, interaction_mode: str) -> str:
        """Enhance prompt based on interaction mode."""

        if interaction_mode == "agent":
            # Agent mode: Code generation focus
            system_prompt = (
                "You are AuraIA, an expert AI coding assistant. "
                "Provide complete, production-ready code solutions with explanations. "
                "Focus on best practices, error handling, and maintainability.\n\n"
            )
            return "".join(
                [
                    system_prompt,
                    "User request: ",
                    prompt,
                    "\n\nProvide a complete code solution:",
                ]
            )

        elif interaction_mode == "edit":
            # Edit mode: Refactoring focus
            system_prompt = (
                "You are AuraIA, a code refactoring expert. "
                "Analyze the code and suggest improvements for readability, performance, and "
                "maintainability. "
                "Explain your changes clearly.\n\n"
            )
            return "".join(
                [
                    system_prompt,
                    "Code to refactor: ",
                    prompt,
                    "\n\nSuggest improvements:",
                ]
            )

        else:  # chat mode
            # Chat mode: Conversational
            system_prompt = (
                "You are AuraIA, a helpful AI assistant. "
                "Provide clear, concise answers. Be friendly and professional.\n\n"
            )
            return "".join(
                [
                    system_prompt,
                    "User: ",
                    prompt,
                    "\n\nAuraIA:",
                ]
            )

    async def _generate_local(
        self, prompt: str, task_type: str, interaction_mode: str, **kwargs
    ) -> Dict[str, Any]:
        """Generate response using local Ollama model."""
        try:
            # Select best local model
            model = self._select_local_model(task_type)

            logger.info(f"🏠 Generating local response with {model}")

            response = await self.ollama_service.query_ollama_async(
                model=model, prompt=prompt, stream=False, **kwargs
            )

            return {
                "success": True,
                "provider": "ollama",
                "model": model,
                "mode": "local",
                "response": response.get("response", ""),
                "reasoning": f"Local LLM ({model}) response",
                "suggestions": self._parse_code_suggestions(
                    response.get("response", ""), interaction_mode
                ),
            }

        except Exception as e:
            logger.error(f"❌ Local LLM generation failed: {e}")
            return {
                "success": False,
                "provider": "ollama",
                "mode": "local",
                "error": str(e),
                "response": ("Sorry, I encountered an error generating a response locally."),
                "reasoning": f"Error: {str(e)}",
                "suggestions": [],
            }

    async def _generate_cloud(
        self, prompt: str, task_type: str, interaction_mode: str, **kwargs
    ) -> Dict[str, Any]:
        """Generate response using cloud LLM provider."""
        try:
            # Prefer OpenAI if available
            if self.openai_api_key:
                return await self._generate_openai(prompt, task_type, interaction_mode, **kwargs)
            elif self.anthropic_api_key:
                return await self._generate_anthropic(prompt, task_type, interaction_mode, **kwargs)
            else:
                # Fallback to local if no cloud API available
                logger.warning(
                    "⚠️ Cloud mode requested but no API keys configured, " "falling back to local"
                )
                return await self._generate_local(prompt, task_type, interaction_mode, **kwargs)

        except Exception as e:
            logger.error(f"❌ Cloud LLM generation failed: {e}")
            # Fallback to local on cloud failure
            logger.info("🔄 Falling back to local LLM")
            return await self._generate_local(prompt, task_type, interaction_mode, **kwargs)

    async def _generate_openai(
        self, prompt: str, task_type: str, interaction_mode: str, **kwargs
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API."""
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.openai_api_key)

            model = "gpt-4o-mini" if task_type in ["chat", "documentation"] else "gpt-4o"

            logger.info(f"☁️ Generating cloud response with OpenAI {model}")

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

            content = response.choices[0].message.content or ""

            return {
                "success": True,
                "provider": "openai",
                "model": model,
                "mode": "cloud",
                "response": content,
                "reasoning": f"Cloud LLM (OpenAI {model}) response",
                "suggestions": self._parse_code_suggestions(content, interaction_mode),
            }

        except ImportError:
            logger.error("❌ OpenAI library not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            raise

    async def _generate_anthropic(
        self, prompt: str, task_type: str, interaction_mode: str, **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Anthropic Claude API."""
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)

            model = (
                "claude-3-haiku-20240307" if task_type in ["chat"] else "claude-3-5-sonnet-20241022"
            )

            logger.info(f"☁️ Generating cloud response with Anthropic {model}")

            message = await client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Anthropic returns a list of block objects; only some have a 'text' attribute
            content = ""
            if getattr(message, "content", None):
                parts: List[str] = []
                for block in message.content:
                    text = getattr(block, "text", None)
                    if isinstance(text, str):
                        parts.append(text)
                content = "\n".join(parts)

            return {
                "success": True,
                "provider": "anthropic",
                "model": model,
                "mode": "cloud",
                "response": content,
                "reasoning": f"Cloud LLM (Anthropic {model}) response",
                "suggestions": self._parse_code_suggestions(content, interaction_mode),
            }

        except ImportError:
            logger.error("❌ Anthropic library not installed. Run: pip install anthropic")
            raise
        except Exception as e:
            logger.error(f"❌ Anthropic API error: {e}")
            raise

    def _select_local_model(self, task_type: str) -> str:
        """Select best available Ollama model for task."""
        available = self.ollama_service.models

        if not available:
            logger.warning("⚠️ No Ollama models detected, using default")
            return self.default_local_model

        # Prefer code-specific models for code tasks
        if task_type in ["code_generation", "refactor"]:
            for model in ["codellama", "deepseek-coder", "codegemma"]:
                matches = [m for m in available if model in m.lower()]
                if matches:
                    return matches[0]

        # Use first available model as fallback
        return available[0]

    def _parse_code_suggestions(self, response: str, interaction_mode: str) -> List[Dict[str, str]]:
        """Parse code blocks from response into suggestions."""
        suggestions = []

        if interaction_mode == "agent":
            # Extract code blocks
            import re

            code_blocks = re.findall(r"```[\w]*\n(.*?)\n```", response, re.DOTALL)

            for idx, code in enumerate(code_blocks):
                suggestions.append(
                    {
                        "description": f"Code solution {idx + 1}",
                        "code": code.strip(),
                    }
                )

        return suggestions
