"""
Dependency Injection Container
Project Creator: Herman Swanepoel
"""

from dependency_injector import containers, providers
from src.core.config import AppSettings, get_settings


class Container(containers.DeclarativeContainer):
    """Application dependency injection container"""

    # Configuration
    config = providers.Singleton(get_settings)

    # Infrastructure services will be registered here
    # Redis, ChromaDB, LLM Manager, Cache, Rate Limiter
