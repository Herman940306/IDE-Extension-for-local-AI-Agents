"""Config tests - Quick coverage boost
Project Creator: Herman Swanepoel
"""

import pytest
from src.config.settings import Settings, get_settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.ollama_base_url == "http://localhost:11434"
        assert s.redis_url == "redis://localhost:6379"
        assert s.api_port == 8000

    def test_custom_values(self):
        s = Settings(api_port=9000, log_level="DEBUG")
        assert s.api_port == 9000
        assert s.log_level == "DEBUG"

    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
