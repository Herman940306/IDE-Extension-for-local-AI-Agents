"""Rapid adapter tests
Herman Swanepoel
"""

import pytest
from unittest.mock import Mock


class TestBaseAdapter:
    def test_import(self):
        from src.adapters.base_adapter import AgentAdapter

        assert AgentAdapter is not None


class TestAdapterUtils:
    def test_import(self):
        from src.adapters.adapter_utils import AdapterUtils

        assert AdapterUtils is not None
