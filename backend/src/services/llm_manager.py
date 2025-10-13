"""
LLM Manager with Ollama support
Project Creator: Herman Swanepoel
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio
import ollama

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMManager:
    """
    Manages LLM interactions with support for local (Ollama) and cloud providers
    """

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OLLAMA,
        model: str = "codellama:7b",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
        allow_cloud: bool = False
    ):
        """
        Initialize LLM Manager
        
        Args:
            provider: LLM provider to use
            model: Model name
            base_url: Base URL for Ollama
            api_key: API key for cloud providers
            allow_cloud: Whether to allow cloud fallback
        """
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.allow_cloud = allow_cloud
        self.ollama_client = None
        
        logger.info(f"LLM Manager initialized with provider: {provider}, model: {model}")

    async def initialize(self) -> None:
        """Initialize the LLM provider"""
        if self.provider == LLMProvider.OLLAMA:
            try:
                # Test connection to Ollama
                await self._test_ollama_connection()
                logger.info("✓ Ollama connection successful")
            except Exception as e:
                logger.error(f"Failed to connect to Ollama: {e}")
                if self.allow_cloud:
                    logger.warning("Ollama unavailable, cloud fallback enabled but not implemented yet")
                else:
                    raise Exception("Ollama unavailable and cloud fallback disabled")

    async def _test_ollama_connection(self) -> None:
        """Test connection to Ollama server"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: ollama.list()
            )
        except Exception as e:
            raise Exception(f"Cannot connect to Ollama at {self.base_url}: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        use_cloud: bool = False
    ) -> str:
        """
        Generate text using the LLM
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            use_cloud: Force cloud usage (if allowed)
            
        Returns:
            Generated text
        """
        if use_cloud and not self.allow_cloud:
            logger.warning("Cloud usage requested but not allowed, using local")
            use_cloud = False

        if self.provider == LLMProvider.OLLAMA and not use_cloud:
            return await self._generate_ollama(prompt, system_prompt, temperature, max_tokens, stop)
        elif use_cloud:
            return await self._generate_cloud(prompt, system_prompt, temperature, max_tokens, stop)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        stop: Optional[List[str]]
    ) -> str:
        """Generate using Ollama"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })

            options = {
                "temperature": temperature,
            }
            
            if max_tokens:
                options["num_predict"] = max_tokens
            
            if stop:
                options["stop"] = stop

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.model,
                    messages=messages,
                    options=options
                )
            )

            return response['message']['content']

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            if self.allow_cloud:
                logger.info("Falling back to cloud provider")
                return await self._generate_cloud(prompt, system_prompt, temperature, max_tokens, stop)
            else:
                raise LLMError(f"LLM generation failed: {e}") from e

    async def _generate_cloud(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        stop: Optional[List[str]]
    ) -> str:
        """Generate using cloud provider (placeholder)"""
        # TODO: Implement cloud providers (OpenAI, Anthropic)
        raise NotImplementedError("Cloud providers not yet implemented")

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ):
        """
        Generate text with streaming response
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            stop: Stop sequences
            
        Yields:
            Text chunks as they are generated
        """
        if self.provider == LLMProvider.OLLAMA:
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })

            options = {
                "temperature": temperature,
            }
            
            if max_tokens:
                options["num_predict"] = max_tokens
            
            if stop:
                options["stop"] = stop

            try:
                # Stream response
                stream = ollama.chat(
                    model=self.model,
                    messages=messages,
                    options=options,
                    stream=True
                )

                for chunk in stream:
                    if 'message' in chunk and 'content' in chunk['message']:
                        yield chunk['message']['content']

            except Exception as e:
                logger.error(f"Streaming generation failed: {e}")
                raise Exception(f"LLM streaming failed: {e}")
        else:
            raise NotImplementedError("Streaming only supported for Ollama currently")

    def get_available_models(self) -> List[str]:
        """
        Get list of available models
        
        Returns:
            List of model names
        """
        if self.provider == LLMProvider.OLLAMA:
            try:
                models = ollama.list()
                return [model['name'] for model in models.get('models', [])]
            except Exception as e:
                logger.error(f"Failed to list models: {e}")
                return []
        else:
            return []

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about current model
        
        Returns:
            Model information dictionary
        """
        return {
            "provider": self.provider.value,
            "model": self.model,
            "base_url": self.base_url if self.provider == LLMProvider.OLLAMA else None,
            "allow_cloud": self.allow_cloud,
        }

    async def health_check(self) -> bool:
        """
        Check if LLM service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if self.provider == LLMProvider.OLLAMA:
                await self._test_ollama_connection()
                return True
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
