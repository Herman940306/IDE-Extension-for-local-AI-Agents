"""
Centralized Configuration Management
Project Creator: Herman Swanepoel
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 50
    redis_min_idle: int = 10
    chroma_persist_dir: str = "./data/chroma"

    class Config:
        env_prefix = "DB_"


class LLMSettings(BaseSettings):
    """LLM configuration"""

    ollama_url: str = "http://localhost:11434"
    default_model: str = "codellama:7b"
    timeout: int = 30
    max_retries: int = 3

    class Config:
        env_prefix = "LLM_"


class CacheSettings(BaseSettings):
    """Cache configuration"""

    enabled: bool = True
    default_ttl: int = 3600
    max_size: int = 1000

    class Config:
        env_prefix = "CACHE_"


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration"""

    enabled: bool = True
    requests_per_minute: int = 60
    burst_size: int = 10

    class Config:
        env_prefix = "RATE_LIMIT_"


class AppSettings(BaseSettings):
    """Application settings"""

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

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


@lru_cache()
def get_settings() -> AppSettings:
    """Get cached settings instance"""
    return AppSettings()
