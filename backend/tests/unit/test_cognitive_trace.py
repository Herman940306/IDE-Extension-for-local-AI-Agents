"""
Unit tests for Cognitive Trace Store
Project Creator: Herman Swanepoel
"""

import pytest
import tempfile
import os
from src.orchestrator.cognitive_trace import CognitiveTraceStore


class TestCognitiveTraceStore:
    """Test suite for CognitiveTraceStore"""
    
    @pytest.fixture
    def temp_trace_file(self):
        """Create temporary trace file"""
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)
    
    def test_initialization(self, temp_trace_file):
        """Test trace store initialization"""
        store = CognitiveTraceStore(path=temp_trace_file)
        assert store.path.exists()
        assert len(store.cache) == 0
    
    def test_record_trace(self, temp_trace_file):
        """Test recording a trace"""
        store = CognitiveTraceStore(path=temp_trace_file)
        
        store.record(
            trace_id="test-123",
            agent="Reasoner",
            action="Generate code",
            confidence=0.9,
            input_hash="abc123",
            output_hash="def456",
            notes="Test trace"
        )
        
        assert len(store.cache) == 1
    
    def test_get_traces(self, temp_trace_file):
        """Test retrieving traces"""
        store = CognitiveTraceStore(path=temp_trace_file)
        
        # Record multiple traces
        for i in range(5):
            store.record(
                trace_id=f"test-{i}",
                agent="Reasoner",
                action=f"Action {i}",
                confidence=0.8 + i * 0.02,
                input_hash=f"input-{i}",
                output_hash=f"output-{i}"
            )
        
        # Flush to disk
        store._flush_cache()
        
        # Retrieve traces
        traces = store.get_traces(limit=3)
        assert len(traces) == 3
    
    def test_filter_by_agent(self, temp_trace_file):
        """Test filtering traces by agent"""
        store = CognitiveTraceStore(path=temp_trace_file)
        
        store.record(
            trace_id="test-1",
            agent="Reasoner",
            action="Action 1",
            confidence=0.9,
            input_hash="in1",
            output_hash="out1"
        )
        
        store.record(
            trace_id="test-2",
            agent="Verifier",
            action="Action 2",
            confidence=0.95,
            input_hash="in2",
            output_hash="out2"
        )
        
        reasoner_traces = store.get_traces(agent="Reasoner")
        assert len(reasoner_traces) == 1
        assert reasoner_traces[0]["agent"] == "Reasoner"
    
    def test_summarize(self, temp_trace_file):
        """Test trace summarization"""
        store = CognitiveTraceStore(path=temp_trace_file)
        
        traces = [
            {
                "agent": "Planner",
                "action": "Decompose task",
                "confidence": 0.9,
                "metadata": {"notes": "Planning phase"}
            },
            {
                "agent": "Reasoner",
                "action": "Generate solution",
                "confidence": 0.85,
                "metadata": {"notes": "Reasoning phase"}
            }
        ]
        
        summary = store.summarize(traces)
        assert "Planner" in summary
        assert "Reasoner" in summary
        assert "0.90" in summary
    
    def test_statistics(self, temp_trace_file):
        """Test trace statistics"""
        store = CognitiveTraceStore(path=temp_trace_file)
        
        for i in range(10):
            store.record(
                trace_id=f"test-{i}",
                agent="Reasoner" if i % 2 == 0 else "Verifier",
                action=f"Action {i}",
                confidence=0.8,
                input_hash=f"in-{i}",
                output_hash=f"out-{i}"
            )
        
        stats = store.get_statistics()
        assert stats["total_traces"] == 10
        assert "Reasoner" in stats["agents"]
        assert "Verifier" in stats["agents"]
        assert stats["avg_confidence"] == 0.8
    
    def test_clear(self, temp_trace_file):
        """Test clearing traces"""
        store = CognitiveTraceStore(path=temp_trace_file)
        
        store.record(
            trace_id="test-1",
            agent="Reasoner",
            action="Action",
            confidence=0.9,
            input_hash="in",
            output_hash="out"
        )
        
        store.clear(keep_file=True)
        assert len(store.cache) == 0
        assert store.path.exists()
