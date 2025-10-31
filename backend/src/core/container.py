"""
Dependency Injection Container
Project Creator: Herman Swanepoel
"""

from __future__ import annotations

from dependency_injector import containers, providers
from src.adapters.base_adapter import AdapterRegistry, AgentConfig, Capability
from src.adapters.crewai_adapter import (
    CREWAI_DEPENDENCIES_AVAILABLE,
    CrewAIDocAgent,
    CrewAITestAgent,
)
from src.agents.bug_agent import BugAgent
from src.agents.doc_agent import DocAgent
from src.agents.refactor_agent import RefactorAgent
from src.agents.test_agent import TestAgent
from src.core.config import get_settings
from src.core.connection_pool import RedisConnectionPool
from src.orchestrator.cognitive_trace import CognitiveTraceStore
from src.orchestrator.meta_controller import MetaController
from src.orchestrator.meta_orchestrator import MetaOrchestrator
from src.orchestrator.multi_model_router import MultiModelRouter
from src.orchestrator.task_router import TaskRouter
from src.services.code_smell_detector import CodeSmellDetector
from src.services.connection_manager import ConnectionManager
from src.services.context import ContextEngine, GraphStore
from src.services.context_manager import ContextManager
from src.services.embeddings_service import EmbeddingsService
from src.services.llm_manager import LLMManager, LLMProvider
from src.services.llm_router import LLMRouter
from src.services.memory_service import MemoryConfig, MemoryService, StorageBackend
from src.services.metrics_service import MetricsService
from src.services.mode_manager import ModeManager, OperationMode
from src.services.ollama_service import get_ollama_service
from src.services.output_composer import OutputComposer
from src.services.predictive_cache_manager import PredictiveCacheManager
from src.services.prompt_templates import PromptTemplates
from src.services.rate_limiter import RateLimiter
from src.services.response_cache import ResponseCache
from src.services.retrieval import build_retriever_dict
from src.services.safety_layer import SafetyLayer
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

    prompt_templates = providers.Singleton(PromptTemplates)

    embeddings_service = providers.Singleton(
        EmbeddingsService,
        model_name=config.provided.embeddings.model_name,
        chroma_persist_dir=config.provided.embeddings.persist_dir,
        collection_name=config.provided.embeddings.collection_name,
        provider=config.provided.embeddings.provider,
        ollama_url=config.provided.embeddings.ollama_url,
        ollama_model_name=config.provided.embeddings.ollama_model_name,
    )

    metrics_service = providers.Singleton(
        MetricsService,
    )

    code_smell_detector = providers.Singleton(
        CodeSmellDetector,
        embeddings_service=embeddings_service,
    )

    semantic_search = providers.Singleton(
        SemanticSearchService,
        embeddings_service=embeddings_service,
        metrics_service=metrics_service,
    )

    context_manager = providers.Singleton(
        ContextManager,
        workspace_path=config.provided.workspace.root_path,
        enable_file_watcher=config.provided.workspace.enable_file_watcher,
    )

    llm_provider = providers.Callable(
        lambda settings: _resolve_llm_provider(settings.llm.provider),
        config,
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

    # Multi-Model Router for intelligent model selection
    multi_model_router = providers.Singleton(MultiModelRouter)

    # Safety Layer for content moderation
    safety_layer = providers.Singleton(
        SafetyLayer,
        llm_manager=llm_manager,
    )

    # Output Composer for tone enhancement
    output_composer = providers.Singleton(
        OutputComposer,
        llm_manager=llm_manager,
    )

    # Context Engine for semantic search
    context_graph_store = providers.Singleton(GraphStore)

    context_engine = providers.Singleton(
        ContextEngine,
        llm_manager=llm_manager,
        graph_store=context_graph_store,
        enabled=config.provided.context_enabled,
        merge_weights=config.provided.context_merge_weights,
    )

    rag_retrievers = providers.Callable(
        lambda enabled, semantic_search_service: build_retriever_dict(
            semantic_search=semantic_search_service if enabled else None,
        ),
        config.provided.experimental_rag_v2_enabled,
        semantic_search_service=semantic_search,
    )

    task_orchestrator = providers.Singleton(
        TaskOrchestrator,
        llm_manager=llm_manager,
        router=multi_model_router,
        safety_layer=safety_layer,
        output_composer=output_composer,
        context_engine=context_engine,
        metrics_service=metrics_service,
        rag_retrievers=rag_retrievers,
    )

    memory_backend = providers.Callable(
        lambda settings: _resolve_storage_backend(settings.memory.backend),
        config,
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
            lambda settings: _resolve_operation_mode(settings.mode.default_mode),
            config,
        ),
    )

    # Reuse the already initialized singleton OllamaService to ensure
    # availability status and models detected during app lifespan are visible
    # to all consumers (e.g., LLMRouter) instead of constructing a fresh instance.
    ollama_service = providers.Object(get_ollama_service())

    llm_router = providers.Singleton(
        LLMRouter,
        mode_manager=mode_manager,
        ollama_service=ollama_service,
        openai_api_key=config.provided.llm.api_key,
        default_local_model=config.provided.llm.default_model,
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

    crewai_doc_agent = (
        providers.Singleton(CrewAIDocAgent)
        if CREWAI_DEPENDENCIES_AVAILABLE
        else providers.Object(None)
    )
    crewai_test_agent = (
        providers.Singleton(CrewAITestAgent)
        if CREWAI_DEPENDENCIES_AVAILABLE
        else providers.Object(None)
    )

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
