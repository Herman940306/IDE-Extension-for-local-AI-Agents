# Design Document - AuraIA Next-Gen Architecture v2.0

**Project Creator:** Herman Swanepoel  
**Version:** 2.0  
**Date:** 2025-10-13

---

## Overview

This document describes the technical design for AuraIA v2.0, a next-generation multi-agent IDE assistant featuring dual-process reasoning, predictive caching, and verifiable output. The system maintains local-first operation while achieving human-like cognitive capabilities.

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                           │
│  • VS Code Extension (TypeScript)                            │
│  • WebSocket Client for real-time communication              │
│  • Analytics Dashboard with cognitive traces                 │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket/REST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cognition Layer (Python)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Meta-Controller (1-2B LLM)                          │  │
│  │  • NetworkX graph-based routing                       │  │
│  │  • Complexity estimation                              │  │
│  │  • Performance-based adaptation                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         ▼               ▼               ▼                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │ Planner  │   │ Reasoner │   │ Verifier │               │
│  │          │   │(System 1)│   │(System 2)│               │
│  │ Decomposes│   │ LLaMA 3B │   │Mistral 7B│               │
│  │   tasks  │   │  <200ms  │   │  <2000ms │               │
│  └──────────┘   └──────────┘   └──────────┘               │
│         │               │               │                   │
│         └───────────────┼───────────────┘                   │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Aggregator + Cognitive Trace Store                  │  │
│  │  • Response synthesis                                 │  │
│  │  • Confidence scoring                                 │  │
│  │  • Thought chain compression                          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Substrate Layer                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Ollama / llama.cpp Runtime                          │  │
│  │  • Q4_K/Q5_K quantized models                        │  │
│  │  • Flash-Attention 2 (CPU)                           │  │
│  │  • Model pooling & hot-swapping                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Memory Systems                                       │  │
│  │  • Redis: Episodic (LRU, 5min TTL)                  │  │
│  │  • FAISS/Chroma: Semantic (embeddings)              │  │
│  │  • LoRA: Procedural (learned behaviors)             │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Safety & Provenance                                  │  │
│  │  • SQLite: Immutable audit logs                       │  │
│  │  • AST Verifier: Syntax validation                    │  │
│  │  • LLM Verifier: Semantic validation                  │  │
│  │  • Guardrails: Safety filters                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Components and Interfaces

### 1. Meta-Controller

**Purpose:** Orchestrate agent communication through dynamic graph routing.

**Interface:**
```python
class MetaController:
    def route(self, task_type: str, complexity: float) -> List[str]
    def update_graph(self, performance_metrics: Dict[str, float]) -> None
    def get_execution_path(self, start: str, end: str) -> List[str]
```

**Implementation Details:**
- Uses NetworkX for graph representation
- Complexity estimation based on code length, AST depth, and task type
- Reinforcement learning for graph optimization
- Supports dynamic edge weight adjustment

### 2. Dual-Process Reasoning

**System 1 (Fast Reasoner):**
- Model: LLaMA 3.2 3B (Q4_K_M)
- Target latency: <200ms
- Use cases: Simple completions, syntax fixes, quick refactors
- Confidence threshold: 0.85

**System 2 (Analytical Verifier):**
- Model: Mistral 7B (Q4_K_M)
- Target latency: <2000ms
- Use cases: Complex refactors, architecture decisions, bug analysis
- Confidence threshold: 0.90

**Interface:**
```python
class DualProcessReasoner:
    def execute(self, task: Task, context: CodeContext) -> AgentResponse
    def should_verify(self, confidence: float) -> bool
```

### 3. Cognitive Trace Store

**Purpose:** Capture and compress reasoning metadata for explainability.

**Schema:**
```json
{
  "trace_id": "uuid",
  "timestamp": "ISO8601",
  "agent": "string",
  "action": "string",
  "confidence": "float",
  "input_hash": "sha256",
  "output_hash": "sha256",
  "metadata": "dict"
}
```

**Interface:**
```python
class CognitiveTraceStore:
    def record(self, agent: str, action: str, confidence: float, **kwargs) -> None
    def get_traces(self, agent: str = None, limit: int = 100) -> List[Dict]
    def summarize(self, traces: List[Dict]) -> str
```

### 4. Memory Systems

**Episodic Memory (Redis):**
```python
class EpisodicCache:
    def store(self, key: str, value: Any, ttl: int = 300) -> None
    def retrieve(self, key: str) -> Optional[Any]
    def delete(self, key: str) -> None
```

**Semantic Memory (FAISS + Chroma):**
```python
class SemanticStore:
    def add_embedding(self, embedding: np.ndarray, metadata: dict) -> None
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple]
    def summarize_cluster(self, cluster_id: int) -> str
```

**Procedural Memory (LoRA):**
```python
class ProceduralMemory:
    def train_adapter(self, training_data: Dict) -> None
    def save_adapter(self, path: str) -> None
    def load_adapter(self, path: str) -> None
    def evaluate_adapter(self, test_data: Dict) -> float
```

### 5. Verifier Ensemble

**Components:**
- AST Checker: Python `ast` module, Tree-sitter for other languages
- LLM Verifier: Mistral 7B with verification prompt
- Guardrails: NeMo filters for safety

**Interface:**
```python
class VerifierEnsemble:
    def verify(self, code: str, language: str, context: str) -> Dict[str, Any]
    def get_confidence(self) -> float
```

**Verification Pipeline:**
1. AST syntax check (fast, deterministic)
2. LLM semantic check (slower, probabilistic)
3. Guardrails safety check (fast, rule-based)
4. Confidence aggregation (weighted average)

### 6. Predictive RL Caching

**Policy Model:** CatBoost classifier

**Features:**
- Hour of day (0-23)
- Language hash (categorical)
- File type hash (categorical)
- Recent action sequence (n-gram)

**Interface:**
```python
class PredictivePolicy:
    def observe(self, event: str, **context) -> None
    def predict(self, current_context: Dict) -> List[str]
    def train(self) -> None
    def evaluate(self) -> float
```

### 7. Provenance Store

**Storage:** SQLite with AES-256 encryption

**Schema:**
```sql
CREATE TABLE provenance (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    task_type TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    confidence REAL NOT NULL,
    metadata TEXT,
    trace_id TEXT REFERENCES cognitive_traces(id)
);
```

---

## Data Models

### Task Model
```python
@dataclass
class Task:
    id: str
    type: TaskType
    priority: Priority
    description: str
    complexity: float  # NEW: 0.0 to 1.0
    metadata: Dict[str, Any]
```

### AgentResponse Model
```python
@dataclass
class AgentResponse:
    task_id: str
    agent_name: str
    suggestions: List[Suggestion]
    confidence: float
    reasoning: str
    cognitive_trace: List[Dict]  # NEW
    verification_result: Optional[Dict]  # NEW
```

### CognitiveTrace Model
```python
@dataclass
class CognitiveTrace:
    trace_id: str
    timestamp: datetime
    agent: str
    action: str
    confidence: float
    input_hash: str
    output_hash: str
    metadata: Dict[str, Any]
```

---

## Error Handling

### Error Hierarchy
```python
class AuraIAError(Exception):
    """Base exception"""

class MetaControllerError(AuraIAError):
    """Routing failures"""

class ReasoningError(AuraIAError):
    """Inference failures"""

class VerificationError(AuraIAError):
    """Verification failures"""

class MemoryError(AuraIAError):
    """Memory system failures"""

class ProvenanceError(AuraIAError):
    """Logging failures"""
```

### Error Recovery Strategies
1. **Routing failure:** Fallback to default path
2. **Inference failure:** Retry with different model
3. **Verification failure:** Request user clarification
4. **Memory failure:** Continue without caching
5. **Provenance failure:** Log to stderr, continue operation

---

## Testing Strategy

### Unit Tests
- Meta-controller routing logic
- Complexity estimation
- Memory operations (Redis, FAISS, LoRA)
- Verifier components (AST, LLM, ensemble)
- Cognitive trace recording and summarization

### Integration Tests
- End-to-end task execution
- Multi-agent coordination
- Memory persistence and retrieval
- Verification pipeline
- Provenance logging

### Performance Tests
- Latency benchmarks (System 1: <200ms, System 2: <2000ms)
- Memory usage monitoring (<2GB total)
- CPU usage monitoring (<60% average)
- Cache hit rate (>60% target)
- Verification confidence (>90% target)

### Safety Tests
- Hallucination detection
- Syntax error prevention
- Semantic correctness validation
- Adversarial input handling

---

## Deployment Architecture

### Local Development
```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Redis
redis-server

# Terminal 3: Backend
uvicorn src.main:app --reload --port 8000

# Terminal 4: Extension
code --extensionDevelopmentPath=./extension
```

### Production Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ./models:/root/.ollama
  
  redis:
    image: redis:alpine
    volumes:
      - ./data/redis:/data
  
  backend:
    build: ./backend
    environment:
      - OLLAMA_URL=http://ollama:11434
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
```

---

## Performance Optimization

### Model Quantization
- All models: GGUF format with Q4_K_M or Q5_K_M quantization
- Memory savings: ~75% vs FP16
- Latency impact: <10% vs FP16

### Flash-Attention 2
- CPU-optimized attention mechanism
- Latency reduction: ~30% for long contexts
- Memory reduction: ~50% for attention layers

### Model Pooling
- Keep System 1 (3B) always loaded
- Load System 2 (7B) on-demand
- Unload after 5 minutes of inactivity

### Predictive Pre-warming
- Pre-load models based on RL policy predictions
- Target: 60% cache hit rate
- Expected latency reduction: 40% for predicted actions

---

## Security Considerations

### Data Privacy
- All inference local (no cloud calls)
- Encrypted provenance logs (AES-256)
- Optional telemetry (opt-in only)
- No PII in logs

### Code Safety
- AST validation before execution
- Semantic verification via LLM
- Guardrails for dangerous patterns
- User confirmation for destructive changes

### Model Safety
- Quantized models from trusted sources
- Checksum verification on load
- Sandboxed execution environment
- Rollback capability for adapters

---

## Monitoring and Observability

### Metrics
- Latency (p50, p95, p99)
- Confidence scores
- Cache hit rates
- Memory usage
- CPU usage
- Verification pass rates

### Logging
- Cognitive traces (JSONL)
- Provenance logs (SQLite)
- Error logs (stderr)
- Performance metrics (Prometheus format)

### Dashboards
- Real-time latency monitoring
- Agent effectiveness tracking
- Memory usage visualization
- Cache performance analysis

---

**Project Creator:** Herman Swanepoel  
**Document Version:** 2.0  
**Last Updated:** 2025-10-13
