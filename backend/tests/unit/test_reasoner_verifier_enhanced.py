"""Tests for FastReasoner"""
import pytest
from unittest.mock import AsyncMock, Mock
from src.models.reasoner import FastReasoner, ReasoningRequest

class TestFastReasoner:
    @pytest.fixture
    def reasoner(self):
        return FastReasoner(ollama_url="http://localhost:11434", model="llama3.2:3b", timeout=30.0)
    
    def test_init(self, reasoner):
        assert reasoner.model == "llama3.2:3b"
    
    def test_build_prompt(self, reasoner):
        req = ReasoningRequest(task_type="refactor", description="test", code_context="code", language="python")
        prompt = reasoner._build_prompt(req)
        assert "Task: refactor" in prompt
