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

    # Celery Configuration
    use_celery: bool = False
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

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
    # System 1 (Fast Reasoner): keep small and responsive
    reasoner_model: str = "llama3.2:3b"
    # Keep resident on GPU for interactive IDE experience
    reasoner_keep_alive: str = "30m"  # Always loaded during session

    # System 2 (Analytical Verifier): default stable 7B, upgrade via env when GPU allows
    verifier_model: str = "mistral:7b"
    # Load on demand; keep resident only while working on complex tasks
    verifier_keep_alive: str = "10m"

    # Optional Advanced Reasoning (CPU fallback when GPU is busy)
    advanced_model: str = "codellama:13b-instruct-q4_0"
    # Force CPU for advanced model to protect GPU VRAM on 1080 Ti
    advanced_force_cpu: bool = True
    # Load only when needed; unload immediately after
    advanced_keep_alive: str = "0"

    # Conversational / UX Layer (chat-style explanations)
    conversational_model: str = "gemma2:9b"
    conversational_keep_alive: str = "0"  # Load on demand; unload after use

    # Embeddings / Search
    # Note: Current embeddings service uses Sentence-Transformers by default.
    # This field declares the preferred Ollama embedding model when enabled.
    preferred_ollama_embedding_model: str = "nomic-embed-text"

    # Summarization / simple NL flows (fallback, CPU-friendly)
    summarizer_model: str = "phi3:mini"
    summarizer_force_cpu: bool = True
    summarizer_keep_alive: str = "5m"  # Load when needed, short residency

    # Safety verification model (optional final check filter; CPU-capable)
    safety_model: str = "phi3:medium"
    safety_force_cpu: bool = True
    safety_keep_alive: str = "-1"  # Always resident on CPU
    enable_safety_check: bool = False

    # Ollama timeouts (seconds)
    reasoner_timeout_seconds: float = 30.0
    verifier_timeout_seconds: float = 60.0

    # Ollama retry policy
    ollama_max_retries: int = 2
    ollama_retry_backoff_seconds: float = 1.0

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
    experimental_rag_v2_enabled: bool = False
    rag_v2_code_top_k: int = 5
    rag_v2_min_relevance: float = 0.0
    rag_v2_memory_message_limit: int = 20
    rag_v2_chain_type: str = "stuff"
    hybrid_fusion_enabled: bool = False
    fusion_weight_bm25: float = 0.4
    fusion_weight_vector: float = 0.6
    reranker_model: str = "bge-reranker-large"
    relevance_threshold: float = 0.7

    # UI/UX Configuration
    show_model_names_in_responses: bool = False  # Hide model routing details from user
    show_system_feedback: bool = False  # Hide backend processing logs from user
    clean_user_experience: bool = True  # Only show user-AI conversation

    # Persona & Emoji (Chat UX)
    enable_omni_persona: bool = True  # Enable AuraIA OmniDev persona in chat
    emoji_enabled_default: bool = True  # Allow emojis in chat responses
    emoji_max_per_response: int = 3  # Hard cap per response (prosody, not decoration)
    emoji_style_default: str = "auto"  # auto|minimal|rich
    # Path to persona assets (emoji library, persona JSONs)
    persona_assets_dir: str = "../AuraIA_Persona"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
