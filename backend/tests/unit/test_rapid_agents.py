"""Rapid agent tests
Herman Swanepoel
"""

import pytest


class TestAgents:
    def test_bug_agent_import(self):
        from src.agents.bug_agent import BugAgent

        assert BugAgent is not None

    def test_doc_agent_import(self):
        from src.agents.doc_agent import DocAgent

        assert DocAgent is not None

    def test_test_agent_import(self):
        from src.agents.test_agent import TestAgent

        assert TestAgent is not None
