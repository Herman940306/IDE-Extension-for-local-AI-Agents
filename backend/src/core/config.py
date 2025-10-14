"""
Centralized Configuration Management
Project Creator: Herman Swanepoel
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    model_config = SettingsConfigDict(env_prefix="DB_", extra="allow")

    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 50
    redis_min_idle: int = 10
    chroma_persist_dir: str = "./data/chroma"


class LLMSettings(BaseSettings):
    """LLM configuration"""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="allow")

    ollama_url: str = "http://localhost:11434"
    default_model: str = "codellama:7b"
    timeout: int = 30
    max_retries: int = 3


class CacheSettings(BaseSettings):
    """Cache configuration"""

    model_config = SettingsConfigDict(env_prefix="CACHE_", extra="allow")

    enabled: bool = True
    default_ttl: int = 3600
    max_size: int = 1000


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration"""

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_", extra="allow")

    enabled: bool = True
    requests_per_minute: int = 60
    burst_size: int = 10


class AppSettings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", extra="allow"  # Allow extra fields from .env
    )

    app_name: str = "Enterprise AI Agents API"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    max_request_size: int = 10 * 1024 * 1024  # 10MB

    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    cache: CacheSettings = CacheSettings()
    rate_limit: RateLimitSettings = RateLimitSettings()


@lru_cache()
def get_settings() -> AppSettings:
    """Get cached settings instance"""
    return AppSettings()
