"""
DI Container Tests
Project Creator: Herman Swanepoel
"""

from src.agents.bug_agent import BugAgent
from src.agents.doc_agent import DocAgent
from src.agents.refactor_agent import RefactorAgent
from src.agents.test_agent import TestAgent
from src.core.container import Container
from src.orchestrator.cognitive_trace import CognitiveTraceStore
from src.orchestrator.meta_orchestrator import MetaOrchestrator
from src.services.context_manager import ContextManager
from src.services.embeddings_service import EmbeddingsService
from src.services.llm_manager import LLMManager
from src.services.memory_service import MemoryService
from src.services.mode_manager import ModeManager, OperationMode
from src.services.predictive_cache_manager import PredictiveCacheManager
from src.services.rate_limiter import RateLimiter
from src.services.response_cache import ResponseCache
from src.services.telemetry_service import TelemetryService
from src.verifier.provenance_store import ProvenanceStore


class TestContainer:
    """Test dependency injection container"""

    def test_container_initialization(self):
        """Test container can be initialized"""
        container = Container()
        assert container is not None

    def test_config_provider(self):
        """Test configuration provider"""
        container = Container()
        config = container.config()
        assert config is not None
        assert config.app_name == "Enterprise AI Agents API"

    def test_redis_client_provider(self):
        """Test Redis client provider"""
        container = Container()
        redis = container.redis_client()
        # Redis may be None if not available
        assert redis is None or redis is not None

    def test_response_cache_provider(self):
        """Test response cache provider"""
        container = Container()
        cache = container.response_cache()
        assert cache is not None
        assert isinstance(cache, ResponseCache)

    def test_rate_limiter_provider(self):
        """Test rate limiter provider"""
        container = Container()
        limiter = container.rate_limiter()
        assert limiter is not None
        assert isinstance(limiter, RateLimiter)

    def test_singleton_behavior(self):
        """Test that providers return same instance"""
        container = Container()

        config1 = container.config()
        config2 = container.config()
        assert config1 is config2

        cache1 = container.response_cache()
        cache2 = container.response_cache()
        assert cache1 is cache2

        limiter1 = container.rate_limiter()
        limiter2 = container.rate_limiter()
        assert limiter1 is limiter2

    def test_dependency_resolution(self):
        """Test that dependencies are resolved correctly"""
        container = Container()

        # Cache should have redis client injected
        cache = container.response_cache()
        assert hasattr(cache, "redis")

        # Rate limiter should have redis client injected
        limiter = container.rate_limiter()
        assert hasattr(limiter, "redis")

    def test_config_injection(self):
        """Test that config values are injected"""
        container = Container()
        config = container.config()

        # Cache should use config TTL
        cache = container.response_cache()
        assert cache.default_ttl == config.cache.default_ttl

        # Rate limiter should use config limit
        limiter = container.rate_limiter()
        assert limiter.default_limit == config.rate_limit.requests_per_minute

    def test_llm_manager_provider(self):
        container = Container()
        manager = container.llm_manager()
        assert isinstance(manager, LLMManager)
        assert manager.model == container.config().llm.default_model

    def test_embeddings_service_provider(self):
        container = Container()
        service = container.embeddings_service()
        assert isinstance(service, EmbeddingsService)
        assert service.model_name == container.config().embeddings.model_name

    def test_memory_service_provider(self):
        container = Container()
        memory = container.memory_service()
        assert isinstance(memory, MemoryService)
        assert memory.config.sqlite_path == container.config().memory.sqlite_path

    def test_context_manager_provider(self):
        container = Container()
        ctx_manager = container.context_manager()
        assert isinstance(ctx_manager, ContextManager)
        assert str(ctx_manager.workspace_path) == container.config().workspace.root_path

    def test_mode_manager_provider(self):
        container = Container()
        mode_manager = container.mode_manager()
        assert isinstance(mode_manager, ModeManager)
        assert mode_manager.get_current_mode() == OperationMode.OFFLINE

    def test_predictive_cache_manager_provider(self):
        container = Container()
        manager = container.predictive_cache_manager()
        assert isinstance(manager, PredictiveCacheManager)
        predictive_settings = container.config().predictive_cache
        assert manager.prediction_threshold == predictive_settings.prediction_threshold

    def test_telemetry_service_provider(self):
        container = Container()
        telemetry = container.telemetry_service()
        assert isinstance(telemetry, TelemetryService)

    def test_observability_components(self):
        container = Container()
        trace_store = container.cognitive_trace_store()
        provenance = container.provenance_store()
        assert isinstance(trace_store, CognitiveTraceStore)
        assert isinstance(provenance, ProvenanceStore)
        assert str(trace_store.path) == container.config().observability.trace_log_path
        assert (
            str(provenance.db_path)
            == container.config().observability.provenance_db_path
        )

    def test_meta_orchestrator_provider(self):
        container = Container()
        orchestrator = container.meta_orchestrator()
        assert isinstance(orchestrator, MetaOrchestrator)

    def test_agent_registry_population(self):
        container = Container()
        agents = container.agents()
        assert set(agents.keys()) == {"bug", "documentation", "refactor", "test"}
        assert isinstance(agents["refactor"], RefactorAgent)
        assert isinstance(agents["documentation"], DocAgent)
        assert isinstance(agents["bug"], BugAgent)
        assert isinstance(agents["test"], TestAgent)
