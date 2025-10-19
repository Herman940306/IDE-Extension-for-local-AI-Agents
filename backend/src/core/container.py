"""
Dependency Injection Container
Project Creator: Herman Swanepoel
"""

from __future__ import annotations

from dependency_injector import containers, providers
from src.adapters.base_adapter import AdapterRegistry, AgentConfig, Capability
from src.adapters.crewai_adapter import CrewAIDocAgent, CrewAITestAgent
from src.agents.bug_agent import BugAgent
from src.agents.doc_agent import DocAgent
from src.agents.refactor_agent import RefactorAgent
from src.agents.test_agent import TestAgent
from src.core.config import get_settings
from src.core.connection_pool import RedisConnectionPool
from src.orchestrator.cognitive_trace import CognitiveTraceStore
from src.orchestrator.meta_controller import MetaController
from src.orchestrator.meta_orchestrator import MetaOrchestrator
from src.orchestrator.task_router import TaskRouter
from src.services.code_smell_detector import CodeSmellDetector
from src.services.connection_manager import ConnectionManager
from src.services.context_manager import ContextManager
from src.services.embeddings_service import EmbeddingsService
from src.services.llm_manager import LLMManager, LLMProvider
from src.services.memory_service import MemoryConfig, MemoryService, StorageBackend
from src.services.mode_manager import ModeManager, OperationMode
from src.services.predictive_cache_manager import PredictiveCacheManager
from src.services.prompt_templates import PromptTemplates
from src.services.rate_limiter import RateLimiter
from src.services.response_cache import ResponseCache
from src.services.semantic_search import SemanticSearchService
from src.services.task_orchestrator import TaskOrchestrator
from src.services.telemetry_service import TelemetryService
from src.verifier.ensemble import VerifierEnsemble
from src.verifier.provenance_store import ProvenanceStore


def _resolve_llm_provider(name: str) -> LLMProvider:
    try:
        return LLMProvider(name.lower())
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported LLM provider: {name}") from exc


def _resolve_storage_backend(name: str) -> StorageBackend:
    try:
        return StorageBackend(name.lower())
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported memory backend: {name}") from exc


def _resolve_operation_mode(name: str) -> OperationMode:
    try:
        return OperationMode(name.lower())
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported operation mode: {name}") from exc


class Container(containers.DeclarativeContainer):
    """Application dependency injection container"""

    config = providers.Singleton(get_settings)

    redis_pool = providers.Singleton(
        RedisConnectionPool,
        url=config.provided.database.redis_url,
        max_connections=config.provided.database.redis_max_connections,
        min_idle=config.provided.database.redis_min_idle,
    )

    # Redis client provider that returns None (since get_client is async)
    # In tests, services should handle None redis_client gracefully
    redis_client = providers.Singleton(lambda pool: None, pool=redis_pool)

    response_cache = providers.Singleton(
        ResponseCache,
        redis_client=redis_client,
        default_ttl=config.provided.cache.default_ttl,
        key_prefix="llm_cache",
    )

    rate_limiter = providers.Singleton(
        RateLimiter,
        redis_client=redis_client,
        default_limit=config.provided.rate_limit.requests_per_minute,
        default_window=60,
    )

    task_orchestrator = providers.Singleton(TaskOrchestrator)

    prompt_templates = providers.Singleton(PromptTemplates)

    embeddings_service = providers.Singleton(
        EmbeddingsService,
        model_name=config.provided.embeddings.model_name,
        chroma_persist_dir=config.provided.embeddings.persist_dir,
        collection_name=config.provided.embeddings.collection_name,
    )

    code_smell_detector = providers.Singleton(
        CodeSmellDetector,
        embeddings_service=embeddings_service,
    )

    semantic_search = providers.Singleton(
        SemanticSearchService,
        embeddings_service=embeddings_service,
    )

    context_manager = providers.Singleton(
        ContextManager,
        workspace_path=config.provided.workspace.root_path,
        enable_file_watcher=config.provided.workspace.enable_file_watcher,
    )

    llm_provider = providers.Callable(
        lambda value: _resolve_llm_provider(value),
        config.provided.llm.provider,
    )

    llm_manager = providers.Singleton(
        LLMManager,
        provider=llm_provider,
        model=config.provided.llm.default_model,
        base_url=config.provided.llm.ollama_url,
        api_key=config.provided.llm.api_key,
        allow_cloud=config.provided.llm.allow_cloud,
        response_cache=response_cache,
        enable_cache=config.provided.llm.enable_cache,
    )

    memory_backend = providers.Callable(
        lambda value: _resolve_storage_backend(value),
        config.provided.memory.backend,
    )

    memory_config = providers.Singleton(
        MemoryConfig,
        backend=memory_backend,
        redis_url=providers.Callable(
            lambda explicit, default: explicit or default,
            config.provided.memory.redis_url,
            config.provided.database.redis_url,
        ),
        sqlite_path=config.provided.memory.sqlite_path,
        max_messages_per_session=config.provided.memory.max_messages_per_session,
        session_ttl_days=config.provided.memory.session_ttl_days,
        hot_data_ttl_hours=config.provided.memory.hot_data_ttl_hours,
        enable_compression=config.provided.memory.enable_compression,
        enable_encryption=config.provided.memory.enable_encryption,
    )

    memory_service = providers.Singleton(
        MemoryService,
        config=memory_config,
    )

    telemetry_service = providers.Singleton(
        TelemetryService,
        max_metrics=config.provided.observability.telemetry_max_metrics,
    )

    predictive_cache_manager = providers.Singleton(
        PredictiveCacheManager,
        prediction_threshold=config.provided.predictive_cache.prediction_threshold,
        preload_window=config.provided.predictive_cache.preload_window,
    )

    mode_manager = providers.Singleton(
        ModeManager,
        default_mode=providers.Callable(
            lambda value: _resolve_operation_mode(value),
            config.provided.mode.default_mode,
        ),
    )

    connection_manager = providers.Singleton(ConnectionManager)

    cognitive_trace_store = providers.Singleton(
        CognitiveTraceStore,
        path=config.provided.observability.trace_log_path,
    )

    observability_encryption_key = providers.Callable(
        lambda key: key or None,
        config.provided.observability.encryption_key,
    )

    provenance_store = providers.Singleton(
        ProvenanceStore,
        db_path=config.provided.observability.provenance_db_path,
        encryption_key=observability_encryption_key,
    )

    verifier_ensemble = providers.Singleton(VerifierEnsemble)

    task_router = providers.Singleton(TaskRouter)
    meta_controller = providers.Singleton(MetaController)

    meta_orchestrator = providers.Singleton(
        MetaOrchestrator,
        llm_manager=llm_manager,
        context_manager=context_manager,
        semantic_search=semantic_search,
    )

    adapter_registry = providers.Singleton(AdapterRegistry)

    crewai_doc_agent = providers.Singleton(CrewAIDocAgent)
    crewai_test_agent = providers.Singleton(CrewAITestAgent)

    refactor_agent_config = providers.Singleton(
        AgentConfig,
        name="Refactor Agent",
        description="Code refactoring specialist",
        capabilities=[Capability.REFACTORING, Capability.CODE_GENERATION],
        enabled=True,
        metadata={"agent_id": "refactor_agent"},
    )

    refactor_agent = providers.Singleton(
        RefactorAgent,
        config=refactor_agent_config,
        llm_manager=llm_manager,
        code_smell_detector=code_smell_detector,
        memory_service=memory_service,
    )

    doc_agent = providers.Singleton(
        DocAgent,
        llm_manager=llm_manager,
        crewai_adapter=crewai_doc_agent,
    )

    test_agent = providers.Singleton(
        TestAgent,
        llm_manager=llm_manager,
    )

    bug_agent = providers.Singleton(
        BugAgent,
        llm_manager=llm_manager,
    )

    agents = providers.Dict(
        bug=bug_agent,
        documentation=doc_agent,
        refactor=refactor_agent,
        test=test_agent,
    )
