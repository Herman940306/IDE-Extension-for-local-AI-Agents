"""
Unit tests for Provenance Store
Project Creator: Herman Swanepoel
"""

import pytest
import tempfile
import os
from src.verifier.provenance_store import ProvenanceStore


class TestProvenanceStore:
    """Test suite for ProvenanceStore"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_initialization(self, temp_db):
        """Test provenance store initialization"""
        store = ProvenanceStore(db_path=temp_db)
        assert store.db_path.exists()
        store.close()

    def test_log_entry(self, temp_db):
        """Test logging provenance entry"""
        store = ProvenanceStore(db_path=temp_db)

        log_id = store.log(
            agent="Reasoner",
            task_type="refactor",
            input_data="def old(): pass",
            output_data="def new(): return True",
            confidence=0.9,
            metadata={"language": "python"},
        )

        assert log_id is not None
        assert len(log_id) == 64  # SHA256 hash
        store.close()

    def test_get_by_id(self, temp_db):
        """Test retrieving entry by ID"""
        store = ProvenanceStore(db_path=temp_db)

        log_id = store.log(
            agent="Reasoner",
            task_type="refactor",
            input_data="test input",
            output_data="test output",
            confidence=0.85,
        )

        entry = store.get_by_id(log_id)
        assert entry is not None
        assert entry["agent"] == "Reasoner"
        assert entry["confidence"] == 0.85
        store.close()

    def test_get_by_agent(self, temp_db):
        """Test retrieving entries by agent"""
        store = ProvenanceStore(db_path=temp_db)

        # Log multiple entries
        for i in range(5):
            store.log(
                agent="Reasoner",
                task_type="refactor",
                input_data=f"input {i}",
                output_data=f"output {i}",
                confidence=0.8,
            )

        entries = store.get_by_agent("Reasoner")
        assert len(entries) == 5
        store.close()

    def test_search_with_filters(self, temp_db):
        """Test searching with filters"""
        store = ProvenanceStore(db_path=temp_db)

        # Log entries with different confidence
        store.log(
            agent="Reasoner",
            task_type="refactor",
            input_data="input1",
            output_data="output1",
            confidence=0.7,
        )

        store.log(
            agent="Reasoner",
            task_type="refactor",
            input_data="input2",
            output_data="output2",
            confidence=0.95,
        )

        # Search with min confidence
        high_conf = store.search(min_confidence=0.9)
        assert len(high_conf) == 1
        assert high_conf[0]["confidence"] == 0.95
        store.close()

    def test_statistics(self, temp_db):
        """Test getting statistics"""
        store = ProvenanceStore(db_path=temp_db)

        # Log entries
        store.log("Reasoner", "refactor", "in1", "out1", 0.9)
        store.log("Verifier", "verify", "in2", "out2", 0.95)
        store.log("Reasoner", "explain", "in3", "out3", 0.85)

        stats = store.get_statistics()
        assert stats["total_entries"] == 3
        assert "Reasoner" in stats["by_agent"]
        assert stats["by_agent"]["Reasoner"]["count"] == 2
        store.close()

    def test_encryption(self, temp_db):
        """Test metadata encryption"""
        store = ProvenanceStore(
            db_path=temp_db, encryption_key="test-encryption-key-32-chars"
        )

        log_id = store.log(
            agent="Reasoner",
            task_type="refactor",
            input_data="input",
            output_data="output",
            confidence=0.9,
            metadata={"sensitive": "data"},
            encrypt=True,
        )

        entry = store.get_by_id(log_id)
        assert entry is not None
        assert entry["metadata"]["sensitive"] == "data"
        store.close()
