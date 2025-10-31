"""
Ollama Service - Auto-detection and Health Checking
Project Creator: Herman Swanepoel
"""

import asyncio
import os
import time
from typing import Any, Dict, Optional

import aiohttp
import requests
from src.core.logging import get_logger

logger = get_logger(__name__)


class OllamaService:
    """Service for Ollama integration with auto-detection and health checks."""

    def __init__(self, host: Optional[str] = None):
        """
        Initialize Ollama service.

        Args:
            host: Ollama host URL. Defaults to environment variable or localhost.
        """
        env_host = os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
        configured_host: str = host if host is not None else env_host
        self.host = configured_host.rstrip("/")
        self._candidate_hosts = [self.host]
        if "localhost" in self.host:
            ipv4_host = self.host.replace("localhost", "127.0.0.1")
            if ipv4_host not in self._candidate_hosts:
                self._candidate_hosts.append(ipv4_host)
        self._is_available = False
        self._version: Optional[str] = None
        self._models: list[str] = []
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(f"🔧 Initializing Ollama service at {self.host}")

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close_session(self):
        if self._session:
            await self._session.close()
            self._session = None

    def _set_active_host(self, host: str) -> None:
        """Promote the working host to the primary slot."""

        normalized = host.rstrip("/")
        self.host = normalized
        unique_hosts = [normalized]
        for candidate in self._candidate_hosts:
            if candidate.rstrip("/") != normalized:
                unique_hosts.append(candidate)
        self._candidate_hosts = unique_hosts

    async def ensure_ollama_async(self, timeout: int = 5, retries: int = 3) -> bool:
        """
        Ensure Ollama is running and accessible asynchronously.

        Args:
            timeout: Request timeout in seconds
            retries: Number of retry attempts

        Returns:
            True if Ollama is available, False otherwise
        """
        session = await self.get_session()
        for attempt in range(retries):
            for candidate in list(self._candidate_hosts):
                try:
                    async with session.get(
                        f"{candidate}/api/version", timeout=timeout
                    ) as response:
                        if response.status == 200:
                            version_data = await response.json()
                            self._version = version_data.get("version", "unknown")
                            self._set_active_host(candidate)
                            self._is_available = True
                            logger.info(f"🧠 Ollama running version: {self._version}")
                            await self._fetch_models_async()
                            return True
                except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                    logger.warning(
                        f"❌ Ollama not detected at {candidate} "
                        f"(attempt {attempt + 1}/{retries})"
                    )
                except Exception as e:
                    logger.error(
                        f"❌ Unexpected error checking Ollama at {candidate}: {e}"
                    )

            if attempt < retries - 1:
                await asyncio.sleep(2)

        self._is_available = False
        logger.error("❌ Ollama service is not available after retries")
        return False

    async def _fetch_models_async(self) -> None:
        """Fetch available models from Ollama asynchronously."""
        session = await self.get_session()
        try:
            async with session.get(f"{self.host}/api/tags", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    self._models = [model["name"] for model in data.get("models", [])]
                    logger.info(
                        f"📦 Available models: {', '.join(self._models[:5])}..."
                    )
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch models: {e}")

    async def generate_async(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Query Ollama with a prompt asynchronously.
        """
        if not self._is_available:
            if not await self.ensure_ollama_async():
                raise RuntimeError(
                    f"Ollama service is not available at {self.host}. "
                    "Please start Ollama service."
                )

        session = await self.get_session()
        payload = {"model": model, "prompt": prompt, "stream": False, **kwargs}

        try:
            async with session.post(
                f"{self.host}/api/generate", json=payload, timeout=60
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"❌ Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Ollama query failed: {e}")
            raise

    def ensure_ollama(self, timeout: int = 5, retries: int = 3) -> bool:
        """
        Ensure Ollama is running and accessible.

        Args:
            timeout: Request timeout in seconds
            retries: Number of retry attempts

        Returns:
            True if Ollama is available, False otherwise
        """
        for attempt in range(retries):
            for candidate in list(self._candidate_hosts):
                try:
                    response = requests.get(f"{candidate}/api/version", timeout=timeout)

                    if response.status_code == 200:
                        version_data = response.json()
                        self._version = version_data.get("version", "unknown")
                        self._set_active_host(candidate)
                        self._is_available = True

                        logger.info(f"🧠 Ollama running version: {self._version}")

                        # Fetch available models
                        self._fetch_models()

                        return True

                except requests.exceptions.ConnectionError:
                    logger.warning(
                        f"❌ Ollama not detected at {candidate} "
                        f"(attempt {attempt + 1}/{retries})"
                    )

                except requests.exceptions.Timeout:
                    logger.warning(
                        f"⏱️ Ollama request timeout (attempt {attempt + 1}/{retries})"
                    )

                except Exception as e:
                    logger.error(
                        f"❌ Unexpected error checking Ollama at {candidate}: {e}"
                    )

            if attempt < retries - 1:
                time.sleep(2)

        self._is_available = False
        logger.error("❌ Ollama service is not available after retries")
        return False

    def _fetch_models(self) -> None:
        """Fetch available models from Ollama."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)

            if response.status_code == 200:
                data = response.json()
                self._models = [model["name"] for model in data.get("models", [])]
                logger.info(f"📦 Available models: {', '.join(self._models[:5])}...")

        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch models: {e}")

    def query_ollama(
        self, model: str, prompt: str, stream: bool = False, **kwargs
    ) -> Any:
        """
        Query Ollama with a prompt.

        Args:
            model: Model name (e.g., 'codellama:7b')
            prompt: Input prompt
            stream: Enable streaming responses
            **kwargs: Additional parameters for Ollama

        Returns:
            Response dictionary from Ollama

        Raises:
            RuntimeError: If Ollama is not available
            requests.HTTPError: If request fails
        """
        if not self._is_available:
            if not self.ensure_ollama():
                raise RuntimeError(
                    f"Ollama service is not available at {self.host}. "
                    "Please start Ollama service."
                )

        payload = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

        try:
            response = requests.post(
                f"{self.host}/api/generate", json=payload, timeout=60, stream=stream
            )
            response.raise_for_status()

            if stream:
                return response
            else:
                return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Ollama query failed: {e}")
            raise

    async def query_ollama_async(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """
        Async version of query_ollama.
        """
        return await self.generate_async(
            model=model,
            prompt=prompt,
            stream=stream,
            **kwargs,
        )

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.

        Returns:
            Health status dictionary
        """
        return {
            "available": self._is_available,
            "host": self.host,
            "version": self._version,
            "models_count": len(self._models),
            "models": self._models[:10],  # First 10 models
        }

    @property
    def is_available(self) -> bool:
        """Check if Ollama is currently available."""
        return self._is_available

    @property
    def version(self) -> Optional[str]:
        """Get Ollama version."""
        return self._version

    @property
    def models(self) -> list[str]:
        """Get list of available models."""
        return self._models


# Singleton instance
_ollama_service: Optional[OllamaService] = None


def get_ollama_service() -> OllamaService:
    """Get singleton Ollama service instance."""
    global _ollama_service

    if _ollama_service is None:
        _ollama_service = OllamaService()
        _ollama_service.ensure_ollama()

    return _ollama_service
