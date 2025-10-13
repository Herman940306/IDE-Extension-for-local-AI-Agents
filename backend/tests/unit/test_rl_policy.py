"""
Unit tests for RL Policy
Project Creator: Herman Swanepoel
"""

import pytest
import tempfile
import os
from src.orchestrator.policies.rl_policy import PredictivePolicy


class TestPredictivePolicy:
    """Test suite for PredictivePolicy"""
    
    def test_initialization(self):
        """Test policy initialization"""
        policy = PredictivePolicy()
        assert len(policy.history) == 0
        assert not policy.is_trained
    
    def test_observe(self):
        """Test observing events"""
        policy = PredictivePolicy(min_history_size=5)
        
        policy.observe(
            event="code_completion",
            language="python",
            hour=10,
            file_type=".py"
        )
        
        assert len(policy.history) == 1
    
    def test_predict_untrained(self):
        """Test prediction before training"""
        policy = PredictivePolicy()
        
        models = policy.predict({
            "hour": 10,
            "language": "python",
            "file_type": ".py"
        })
        
        assert len(models) > 0
        assert "llama3.2:3b" in models
    
    def test_train(self):
        """Test model training"""
        policy = PredictivePolicy(min_history_size=10)
        
        # Add observations
        for i in range(20):
            policy.observe(
                event="code_completion" if i % 2 == 0 else "refactor",
                language="python",
                hour=10 + (i % 12),
                file_type=".py"
            )
        
        # Train
        success = policy.train()
        assert success
        assert policy.is_trained
