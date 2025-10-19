"""
Application Settings
Project Creator: Herman Swanepoel
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables"""

    model_config = SettingsConfigDict(
        extra="allow",
        env_file=".env",
        case_sensitive=False,  # Allow extra fields from .env file
    )

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None

    # ChromaDB Configuration
    chroma_persist_dir: str = "./data/chroma_db"

    # FAISS Configuration
    faiss_index_path: str = "./data/faiss_index"

    # LoRA Adapters
    lora_adapters_path: str = "./data/lora_adapters"

    # Provenance & Logging
    provenance_db_path: str = "./data/provenance.db"
    cognitive_trace_path: str = "./data/trace_logs.jsonl"

    # Model Configuration
    reasoner_model: str = "llama3.2:3b-q4_K_M"
    verifier_model: str = "mistral:7b-q4_K_M"
    summarizer_model: str = "phi3:mini-q4_K_M"

    # Performance Tuning
    omp_num_threads: int = 7
    flash_attention_enabled: bool = True

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # Security
    secret_key: str = "change-me-in-production"
    encryption_key: str = "change-me-in-production"

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/aura_ia.log"

    # Feature Flags
    enable_cognitive_traces: bool = True
    enable_predictive_caching: bool = True
    enable_continual_learning: bool = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
