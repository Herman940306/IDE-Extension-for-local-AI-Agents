# AuraIA Next-Gen Implementation Checklist

**Project:** AuraIA IDE Extension for Local AI Agents  
**Version:** 2.0 (Next-Gen Architecture Integration)  
**Author:** Software Architect GPT (for Herman Swanepoel)  
**Date:** 2025-10-13  
**Project Creator:** Herman Swanepoel

---

## 🚀 Objective

Provide a concrete step-by-step plan to implement the new multi-agent, CPU-optimized architecture defined in `ARCHITECTURE_V2_NEXTGEN.md`.

---

## 🧱 1. Backend Setup (FastAPI + Orchestrator)

### ✅ Step 1 — Repository Preparation

- [ ] Create a new branch: `feature/nextgen-architecture-v2`
- [ ] Update Python dependencies:

```bash
pip install fastapi uvicorn networkx faiss-cpu redis chromadb torch transformers peft accelerate catboost
```

- [ ] Add `requirements_nextgen.txt` file with pinned versions.

### ✅ Step 2 — Core Directories

```
backend/src/
├── orchestrator/
│   ├── meta_controller.py       # Graph-based routing logic
│   ├── task_router.py           # Intent detection & assignment
│   ├── cognitive_trace.py       # Thought chain store
│   └── policies/                # RL cache policies
│       ├── rl_policy.py
│       └── catboost_predictor.py
├── memory/
│   ├── episodic_cache.py        # Redis (LRU)
│   ├── semantic_store.py        # FAISS + Chroma
│   └── procedural_lora.py       # LoRA/TinyLoRA adapters
├── verifier/
│   ├── ast_checker.py           # Syntax validation
│   ├── llm_verifier.py          # Neural validation
│   └── ensemble.py              # Combines AST + LLM checks
├── models/
│   ├── reasoner.py              # Fast reasoning model (System 1)
│   ├── verifier.py              # Analytical model (System 2)
│   ├── summarizer.py            # Cognitive trace summarizer
│   └── adapters/                # llama.cpp / Ollama wrappers
│       ├── ollama_wrapper.py
│       └── llamacpp_wrapper.py
└── api/
    ├── routes.py                # REST endpoints
    └── websocket.py             # Real-time IDE communication
```

---

## 🧠 2. Implement Meta-Controller

### Purpose

Supervise dynamic agent communication through a **graph-based reasoning topology**.

```python
# backend/src/orchestrator/meta_controller.py
import networkx as nx
from typing import List, Dict, Any

class MetaController:
    """
    Meta-controller for dynamic agent orchestration
    Project Creator: Herman Swanepoel
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_default_graph()

    def _build_default_graph(self):
        """Build default reasoning graph"""
        self.graph.add_edges_from([
            ("Planner", "Reasoner"),
            ("Reasoner", "Verifier"),
            ("Verifier", "Aggregator")
        ])

    def route(self, task_type: str, complexity: float) -> List[str]:
        """
        Determine execution path based on task characteristics

        Args:
            task_type: Type of task (refactor, explain, generate)
            complexity: Complexity score (0.0 to 1.0)

        Returns:
            List of agent names in execution order
        """
        if complexity < 0.3:
            # Simple task: skip verifier
            return ["Reasoner", "Aggregator"]
        else:
            # Complex task: full pipeline
            return nx.shortest_path(self.graph, "Planner", "Aggregator")

    def update_graph(self, performance_metrics: Dict[str, float]):
        """
        Dynamically adjust graph based on performance

        Args:
            performance_metrics: Agent performance scores
        """
        # Implement reinforcement learning logic
        pass
```

### To-Do

- [ ] Integrate into FastAPI `/route` endpoint.
- [ ] Enable live graph reconfiguration (based on confidence metrics).
- [ ] Add complexity estimation model.

---

## 🧩 3. Cognitive Trace Store

### Purpose

Capture reasoning metadata from each agent to ensure explainability.

```python
# backend/src/orchestrator/cognitive_trace.py
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

class CognitiveTraceStore:
    """
    Store and manage cognitive traces for explainability
    Project Creator: Herman Swanepoel
    """

    def __init__(self, path: str = "./data/trace_logs.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        agent: str,
        action: str,
        confidence: float,
        notes: str = "",
        metadata: Dict[str, Any] = None
    ):
        """Record a cognitive trace entry"""
        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "action": action,
            "confidence": confidence,
            "notes": notes,
            "metadata": metadata or {}
        }

        with open(self.path, "a") as f:
            f.write(json.dumps(log) + "\n")

    def get_traces(
        self,
        agent: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve recent traces"""
        traces = []

        if not self.path.exists():
            return traces

        with open(self.path, "r") as f:
            for line in f:
                trace = json.loads(line)
                if agent is None or trace["agent"] == agent:
                    traces.append(trace)
                    if len(traces) >= limit:
                        break

        return traces[-limit:]

    def summarize(self, traces: List[Dict[str, Any]]) -> str:
        """
        Summarize traces using a small LLM

        Args:
            traces: List of trace entries

        Returns:
            Human-readable summary
        """
        # TODO: Implement with Phi-3-mini or Gemma-2B
        summary = f"Processed {len(traces)} reasoning steps:\n"
        for trace in traces:
            summary += f"- {trace['agent']}: {trace['action']} (confidence: {trace['confidence']:.2f})\n"
        return summary
```

### To-Do

- [ ] Add summarizer model (Phi-3-mini / Gemma-2B) to compress logs.
- [ ] Connect with Redis for real-time analytics.
- [ ] Implement trace visualization endpoint.

---

## ⚙️ 4. Memory Layer Integration

### Episodic Memory (Short-Term)

```python
# backend/src/memory/episodic_cache.py
import redis
from typing import Any, Optional

class EpisodicCache:
    """
    Short-term conversation state using Redis LRU
    Project Creator: Herman Swanepoel
    """

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.client = redis.Redis(host=host, port=port, decode_responses=True)

    def store(self, key: str, value: Any, ttl: int = 300):
        """Store with time-to-live"""
        self.client.set(key, value, ex=ttl)

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve from cache"""
        return self.client.get(key)

    def delete(self, key: str):
        """Remove from cache"""
        self.client.delete(key)
```

### Semantic Memory (Long-Term)

```python
# backend/src/memory/semantic_store.py
import faiss
import numpy as np
from typing import List, Tuple
import chromadb

class SemanticStore:
    """
    Long-term embeddings for code patterns
    Project Creator: Herman Swanepoel
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.create_collection("code_patterns")

    def add_embedding(self, embedding: np.ndarray, metadata: dict):
        """Add code embedding to store"""
        self.index.add(embedding.reshape(1, -1))
        self.collection.add(
            embeddings=[embedding.tolist()],
            metadatas=[metadata],
            ids=[metadata["id"]]
        )

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[float, dict]]:
        """Search for similar code patterns"""
        distances, indices = self.index.search(query_embedding.reshape(1, -1), k)

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=k
        )

        return list(zip(distances[0], results["metadatas"][0]))
```

### Procedural Memory (LoRA)

```python
# backend/src/memory/procedural_lora.py
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM
from typing import Dict, Any

class ProceduralMemory:
    """
    Learned behaviors using LoRA adapters
    Project Creator: Herman Swanepoel
    """

    def __init__(self, base_model_name: str):
        self.base_model = AutoModelForCausalLM.from_pretrained(base_model_name)
        self.lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=8,
            lora_alpha=32,
            lora_dropout=0.1
        )
        self.model = get_peft_model(self.base_model, self.lora_config)

    def train_adapter(self, training_data: Dict[str, Any]):
        """Train LoRA adapter on user feedback"""
        # TODO: Implement training loop
        pass

    def save_adapter(self, path: str):
        """Save trained adapter"""
        self.model.save_pretrained(path)

    def load_adapter(self, path: str):
        """Load trained adapter"""
        self.model.load_adapter(path)
```

### To-Do

- [ ] Use FAISS for vector similarity search.
- [ ] Schedule summarization tasks.
- [ ] Build embedding store for code patterns.
- [ ] Integrate `peft` for adapter management.
- [ ] Implement background fine-tuning task (async).

---

## 🧩 5. Verifier Ensemble

```python
# backend/src/verifier/ensemble.py
import ast
from typing import Dict, Any

class ASTChecker:
    """Syntax validation using AST parsing"""

    def validate(self, code: str, language: str = "python") -> bool:
        """Check if code is syntactically valid"""
        if language == "python":
            try:
                ast.parse(code)
                return True
            except SyntaxError:
                return False
        # Add support for other languages
        return True

class LLMVerifier:
    """Semantic validation using LLM"""

    def __init__(self, model):
        self.model = model

    def evaluate(self, code: str, context: str) -> Dict[str, Any]:
        """Evaluate code logic and semantics"""
        prompt = f"Verify this code is logically correct:\n{code}\n\nContext: {context}"
        response = self.model.generate(prompt)
        return {
            "valid": "correct" in response.lower(),
            "reasoning": response
        }

class VerifierEnsemble:
    """
    Combined AST + LLM verification
    Project Creator: Herman Swanepoel
    """

    def __init__(self, ast_checker: ASTChecker, llm_verifier: LLMVerifier):
        self.ast_checker = ast_checker
        self.llm_verifier = llm_verifier

    def verify(self, code: str, language: str, context: str) -> Dict[str, Any]:
        """Run full verification pipeline"""
        ast_valid = self.ast_checker.validate(code, language)

        if not ast_valid:
            return {
                "valid": False,
                "reason": "Syntax error detected",
                "confidence": 1.0
            }

        llm_result = self.llm_verifier.evaluate(code, context)

        return {
            "valid": llm_result["valid"],
            "reason": llm_result["reasoning"],
            "confidence": 0.9 if llm_result["valid"] else 0.3
        }
```

### To-Do

- [ ] Use AST parsing for static syntax checks.
- [ ] Add LLM verifier for semantic logic validation.
- [ ] Integrate with Mistral 7B for System 2 reasoning.

---

## 🧮 6. Predictive RL Caching

```python
# backend/src/orchestrator/policies/rl_policy.py
from catboost import CatBoostClassifier
import numpy as np
from typing import Dict, List

class PredictivePolicy:
    """
    Reinforcement learning policy for predictive caching
    Project Creator: Herman Swanepoel
    """

    def __init__(self):
        self.model = CatBoostClassifier(iterations=100, depth=4, verbose=False)
        self.history = []

    def observe(self, event: str, language: str, hour: int, file_type: str):
        """Record user activity"""
        self.history.append({
            "event": event,
            "language": language,
            "hour": hour,
            "file_type": file_type
        })

    def predict(self, current_context: Dict) -> List[str]:
        """
        Predict next likely actions

        Returns:
            List of models to pre-warm
        """
        # Feature engineering
        features = [
            current_context["hour"],
            hash(current_context["language"]) % 100,
            hash(current_context["file_type"]) % 100
        ]

        # Predict next action
        if len(self.history) > 100:
            # Train model on history
            X = np.array([[h["hour"], hash(h["language"]) % 100, hash(h["file_type"]) % 100]
                          for h in self.history[:-1]])
            y = [h["event"] for h in self.history[1:]]
            self.model.fit(X, y)

            prediction = self.model.predict([features])[0]
            return self._action_to_models(prediction)

        return []

    def _action_to_models(self, action: str) -> List[str]:
        """Map predicted action to required models"""
        mapping = {
            "code_completion": ["llama3.2:3b"],
            "refactor": ["mistral:7b"],
            "explain": ["codellama:7b"]
        }
        return mapping.get(action, [])
```

### To-Do

- [ ] Implement lightweight CatBoost or PPO policy in `/orchestrator/policies/`.
- [ ] Train on user telemetry (file open, edit frequency, time of day).
- [ ] Use predictions to pre-load agents/models.

---

## 🛡️ 7. Safety & Provenance

```python
# backend/src/verifier/provenance_store.py
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any

class ProvenanceStore:
    """
    Immutable audit logs for all inferences
    Project Creator: Herman Swanepoel
    """

    def __init__(self, db_path: str = "./data/provenance.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        """Create provenance table"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS provenance (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                task_type TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                output_hash TEXT NOT NULL,
                confidence REAL NOT NULL,
                metadata TEXT
            )
        """)
        self.conn.commit()

    def log(
        self,
        agent: str,
        task_type: str,
        input_data: str,
        output_data: str,
        confidence: float,
        metadata: Dict[str, Any] = None
    ):
        """Log inference with provenance"""
        log_id = hashlib.sha256(
            f"{agent}{task_type}{input_data}{datetime.utcnow()}".encode()
        ).hexdigest()

        input_hash = hashlib.sha256(input_data.encode()).hexdigest()
        output_hash = hashlib.sha256(output_data.encode()).hexdigest()

        self.conn.execute("""
            INSERT INTO provenance
            (id, timestamp, agent, task_type, input_hash, output_hash, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            datetime.utcnow().isoformat(),
            agent,
            task_type,
            input_hash,
            output_hash,
            confidence,
            str(metadata or {})
        ))
        self.conn.commit()
```

### To-Do

- [ ] Create `provenance_store.py` using SQLite for immutable logs.
- [ ] Encrypt logs with AES-256.
- [ ] Set confidence threshold = 0.85 minimum for final response approval.

---

## 🧪 8. Testing Strategy

### Unit Tests

```python
# backend/tests/unit/test_meta_controller.py
import pytest
from src.orchestrator.meta_controller import MetaController

def test_simple_task_routing():
    controller = MetaController()
    path = controller.route(task_type="refactor", complexity=0.2)
    assert path == ["Reasoner", "Aggregator"]

def test_complex_task_routing():
    controller = MetaController()
    path = controller.route(task_type="refactor", complexity=0.8)
    assert "Verifier" in path
```

### Integration Tests

```python
# backend/tests/integration/test_verifier_ensemble.py
import pytest
from src.verifier.ensemble import VerifierEnsemble, ASTChecker, LLMVerifier

@pytest.mark.asyncio
async def test_valid_code_verification():
    ast_checker = ASTChecker()
    llm_verifier = LLMVerifier(model=mock_model)
    ensemble = VerifierEnsemble(ast_checker, llm_verifier)

    result = ensemble.verify(
        code="def hello(): return 'world'",
        language="python",
        context="Simple function"
    )

    assert result["valid"] == True
```

### E2E Tests

- [ ] Simulate VS Code request → multi-agent → response cycle.

### To-Do

- [ ] `pytest tests/unit/` for meta-controller, caches, verifiers.
- [ ] Test FastAPI endpoints (`/route`, `/infer`, `/verify`).
- [ ] Add performance benchmarks.

---

## 🧭 9. Deployment Configuration

```bash
# Start local runtime
ollama serve &

# Start Redis
redis-server &

# Start FastAPI backend
uvicorn src.main:app --port 8000 --reload
```

### Environment Variables

```bash
# .env
OLLAMA_BASE_URL=http://localhost:11434
REDIS_URL=redis://localhost:6379
CHROMA_PERSIST_DIR=./data/chroma_db
FAISS_INDEX_PATH=./data/faiss_index
LORA_ADAPTERS_PATH=./data/lora_adapters
PROVENANCE_DB_PATH=./data/provenance.db
COGNITIVE_TRACE_PATH=./data/trace_logs.jsonl

# Model configuration
REASONER_MODEL=llama3.2:3b-q4_K_M
VERIFIER_MODEL=mistral:7b-q4_K_M
SUMMARIZER_MODEL=phi3:mini-q4_K_M

# Performance tuning
OMP_NUM_THREADS=7
FLASH_ATTENTION_ENABLED=true
```

### To-Do

- [ ] Add `.env` variables for configurable model paths.
- [ ] Use supervisor or pm2 to manage background processes.
- [ ] Create Docker Compose configuration.

---

## 📈 10. Milestones Summary

| Phase | Deliverable                 | Timeline | Status         |
| ----- | --------------------------- | -------- | -------------- |
| **1** | Meta-Controller prototype   | Week 1   | ⬜ Not Started |
| **2** | Cognitive Trace integration | Week 2   | ⬜ Not Started |
| **3** | Memory layering complete    | Week 3   | ⬜ Not Started |
| **4** | Verifier ensemble active    | Week 4   | ⬜ Not Started |
| **5** | RL caching online           | Week 6   | ⬜ Not Started |
| **6** | End-to-end test run         | Week 8   | ⬜ Not Started |

---

## 📊 Success Metrics

### Performance Targets

- [ ] Latency reduction: 35-50% vs current system
- [ ] Verification confidence: >90% on code generation
- [ ] Cache hit rate: >60% for predictive caching
- [ ] Memory usage: <2GB total (all models + caches)
- [ ] CPU usage: <60% during active inference

### Quality Targets

- [ ] Test coverage: >85% for all new modules
- [ ] Zero critical security vulnerabilities
- [ ] Full cognitive trace for all inferences
- [ ] Rollback capability for failed adaptations

---

**End of Implementation Checklist**

_This guide provides the exact scaffolding for upgrading AuraIA's backend to a self-learning, verifiable local AI IDE assistant._

**Project Creator:** Herman Swanepoel  
**Document Version:** 2.0  
**Last Updated:** 2025-10-13
