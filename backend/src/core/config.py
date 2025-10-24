"""
Centralized Configuration Management
Project Creator: Herman Swanepoel
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
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

    provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    default_model: str = "codellama:7b"
    timeout: int = 30
    max_retries: int = 3
    allow_cloud: bool = False
    api_key: Optional[str] = None
    enable_cache: bool = True


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


class WorkspaceSettings(BaseSettings):
    """Workspace configuration"""

    model_config = SettingsConfigDict(env_prefix="WORKSPACE_", extra="allow")

    root_path: str = "."
    enable_file_watcher: bool = False


class MemorySettings(BaseSettings):
    """Memory service configuration"""

    model_config = SettingsConfigDict(env_prefix="MEMORY_", extra="allow")

    backend: str = "hybrid"
    redis_url: Optional[str] = None
    sqlite_path: str = "data/sessions/memory.db"
    max_messages_per_session: int = 1000
    session_ttl_days: int = 30
    hot_data_ttl_hours: int = 24
    enable_compression: bool = True
    enable_encryption: bool = False


class EmbeddingsSettings(BaseSettings):
    """Embeddings service configuration"""

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDINGS_", extra="allow", protected_namespaces=("settings_",)
    )

    # Default provider remains Sentence-Transformers for backward compatibility
    provider: str = "sentence-transformers"  # or "ollama"
    model_name: str = "microsoft/codebert-base"
    persist_dir: str = "./data/chroma"
    collection_name: str = "code_embeddings"

    # Ollama embeddings (optional)
    ollama_url: str = "http://localhost:11434"
    ollama_model_name: str = "nomic-embed-text"


class ObservabilitySettings(BaseSettings):
    """Observability and logging configuration"""

    model_config = SettingsConfigDict(env_prefix="OBS_", extra="allow")

    trace_log_path: str = "./data/trace_logs.jsonl"
    provenance_db_path: str = "./data/provenance.db"
    encryption_key: Optional[str] = None
    telemetry_max_metrics: int = 10000

    @field_validator("trace_log_path", "provenance_db_path", mode="after")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        """Normalize paths for cross-platform consistency"""
        if value.startswith("./"):
            return value
        return str(Path(value))


class PredictiveCacheSettings(BaseSettings):
    """Predictive caching configuration"""

    model_config = SettingsConfigDict(env_prefix="PREDICTIVE_CACHE_", extra="allow")

    enabled: bool = True
    prediction_threshold: float = 0.6
    preload_window: float = 60.0
    background_interval: float = 30.0


class ModeSettings(BaseSettings):
    """Operation mode configuration"""

    model_config = SettingsConfigDict(env_prefix="MODE_", extra="allow")

    default_mode: str = "offline"


class AppSettings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.production"),
        env_nested_delimiter="__",
        extra="allow",  # Allow extra fields from env files
    )

    app_name: str = "Enterprise AI Agents API"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    cache: CacheSettings = CacheSettings()
    rate_limit: RateLimitSettings = RateLimitSettings()
    workspace: WorkspaceSettings = WorkspaceSettings()
    memory: MemorySettings = MemorySettings()
    embeddings: EmbeddingsSettings = EmbeddingsSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    predictive_cache: PredictiveCacheSettings = PredictiveCacheSettings()
    mode: ModeSettings = ModeSettings()

    # Background processing (Celery)
    # These are optional and default to Redis when not provided
    use_celery: bool = False
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None


@lru_cache()
def get_settings() -> AppSettings:
    """Get cached settings instance"""
    return AppSettings()
