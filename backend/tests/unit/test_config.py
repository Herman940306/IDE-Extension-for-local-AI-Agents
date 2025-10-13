"""
Configuration Tests
Project Creator: Herman Swanepoel
"""

from src.core.config import (
    DatabaseSettings,
    LLMSettings,
    CacheSettings,
    RateLimitSettings,
    AppSettings,
    get_settings,
)


class TestDatabaseSettings:
    """Test database configuration"""

    def test_default_values(self):
        """Test default database settings"""
        settings = DatabaseSettings()
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.redis_max_connections == 50
        assert settings.redis_min_idle == 10
        assert settings.chroma_persist_dir == "./data/chroma"

    def test_env_override(self, monkeypatch):
        """Test environment variable override"""
        monkeypatch.setenv("DB_REDIS_URL", "redis://custom:6380")
        monkeypatch.setenv("DB_REDIS_MAX_CONNECTIONS", "100")
        settings = DatabaseSettings()
        assert settings.redis_url == "redis://custom:6380"
        assert settings.redis_max_connections == 100


class TestLLMSettings:
    """Test LLM configuration"""

    def test_default_values(self):
        """Test default LLM settings"""
        settings = LLMSettings()
        assert settings.ollama_url == "http://localhost:11434"
        assert settings.default_model == "codellama:7b"
        assert settings.timeout == 30
        assert settings.max_retries == 3

    def test_env_override(self, monkeypatch):
        """Test environment variable override"""
        monkeypatch.setenv("LLM_OLLAMA_URL", "http://custom:11435")
        monkeypatch.setenv("LLM_TIMEOUT", "60")
        settings = LLMSettings()
        assert settings.ollama_url == "http://custom:11435"
        assert settings.timeout == 60


class TestCacheSettings:
    """Test cache configuration"""

    def test_default_values(self):
        """Test default cache settings"""
        settings = CacheSettings()
        assert settings.enabled is True
        assert settings.default_ttl == 3600
        assert settings.max_size == 1000

    def test_env_override(self, monkeypatch):
        """Test environment variable override"""
        monkeypatch.setenv("CACHE_ENABLED", "false")
        monkeypatch.setenv("CACHE_DEFAULT_TTL", "7200")
        settings = CacheSettings()
        assert settings.enabled is False
        assert settings.default_ttl == 7200


class TestRateLimitSettings:
    """Test rate limit configuration"""

    def test_default_values(self):
        """Test default rate limit settings"""
        settings = RateLimitSettings()
        assert settings.enabled is True
        assert settings.requests_per_minute == 60
        assert settings.burst_size == 10

    def test_env_override(self, monkeypatch):
        """Test environment variable override"""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120")
        settings = RateLimitSettings()
        assert settings.enabled is False
        assert settings.requests_per_minute == 120


class TestAppSettings:
    """Test application settings"""

    def test_default_values(self):
        """Test default app settings"""
        settings = AppSettings()
        assert settings.app_name == "Enterprise AI Agents API"
        assert settings.version == "1.0.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.max_request_size == 10 * 1024 * 1024

    def test_nested_settings(self):
        """Test nested settings initialization"""
        settings = AppSettings()
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.llm, LLMSettings)
        assert isinstance(settings.cache, CacheSettings)
        assert isinstance(settings.rate_limit, RateLimitSettings)

    def test_env_override(self, monkeypatch):
        """Test environment variable override"""
        monkeypatch.setenv("APP_NAME", "Custom API")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = AppSettings()
        assert settings.app_name == "Custom API"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"

    def test_component_settings_access(self):
        """Test accessing component settings"""
        settings = AppSettings()
        assert settings.database.redis_url == "redis://localhost:6379"
        assert settings.llm.timeout == 30
        assert settings.cache.enabled is True
        assert settings.rate_limit.requests_per_minute == 60


class TestGetSettings:
    """Test settings singleton"""

    def test_singleton_behavior(self):
        """Test that get_settings returns same instance"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_cached_instance(self):
        """Test that settings are cached"""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert id(settings1) == id(settings2)
