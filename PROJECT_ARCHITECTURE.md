# 🎯 AuraIA Project Architecture & Summary

**Project Creator:** Herman Swanepoel  
**Version:** Beta Deployment Phase (Week 3-8)  
**Last Updated:** 2025-10-13

---

## 📋 Project Goal

**AuraIA** is an **AI-augmented IDE extension** (VS Code) that provides intelligent code assistance through a **multi-agent orchestration system**. The goal is to create a production-ready developer productivity platform that combines:

- **Local-first AI inference** (privacy-focused, edge computing)
- **Multi-agent collaboration** (specialized agents for different tasks)
- **Enterprise framework integration** (SuperAGI, AutoGPT, LangChain, CrewAI)
- **Real-time code intelligence** (inline suggestions, refactoring, bug detection)
- **Analytics and learning** (ML-driven optimization, user pattern analysis)

---

## 🏗️ Current Architecture

### **1. IDE Extension (Frontend)**
**Location:** `extension/src/`

**Key Features:**
- ✅ **Inline Code Suggestions** - Real-time AI-powered code completions
- ✅ **Agent Discussion Panel** - Chat interface for complex queries
- ✅ **Code Actions** - Context-aware refactoring, explanation, optimization
- ✅ **Analytics Dashboard** - Productivity metrics, agent effectiveness tracking
- ✅ **Multi-language Support** - Python, TypeScript, JavaScript, Java, etc.
- 🚧 **Accessibility Features** - WCAG compliance (in progress)

**Tech Stack:**
- TypeScript
- VS Code Extension API
- WebSocket for real-time communication
- Chart.js for analytics visualization

---

### **2. Backend AI System (Multi-Agent Orchestration)**
**Location:** `backend/src/`

**Architecture Pattern:** **Hexagonal Architecture** (Ports & Adapters)

```
┌─────────────────────────────────────────────────────────┐
│                    IDE Extension                         │
│              (VS Code WebView + WebSocket)               │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket/REST
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Agent Orchestration Layer               │   │
│  │  - Task routing & prioritization                │   │
│  │  - Multi-agent coordination                     │   │
│  │  - Response aggregation                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Agent Adapters (Unified Interface)     │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  • Ollama Adapter (Local LLMs)                   │  │
│  │  • LangChain Adapter (RAG, chains)               │  │
│  │  • CrewAI Adapter (Role-based agents)            │  │
│  │  • SuperAGI Adapter (Autonomous execution) ✅    │  │
│  │  • AutoGPT Adapter (Research & planning) ✅      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Infrastructure Services                   │  │
│  │  • ChromaDB (Vector embeddings, RAG)             │  │
│  │  • Redis (Session cache, rate limiting)          │  │
│  │  • Analytics Service (ML telemetry)              │  │
│  │  • Context Manager (Code analysis)               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Local AI Runtime (Ollama)                   │
│  • LLaMA 3.2 (3B) - Fast inline suggestions             │
│  • CodeLLaMA (7B) - Code generation                     │
│  • Mistral (7B) - General reasoning                     │
│  • DeepSeek Coder - Specialized code tasks              │
└─────────────────────────────────────────────────────────┘
```

---

## 🤖 Multi-Agent Integration Strategy

### **Current Implementation:**

#### **1. Adapter Pattern (Unified Interface)**
All agents implement the same interface:
```python
class AgentAdapter:
    async def initialize() -> None
    async def execute_task(task: Task, context: CodeContext) -> AgentResponse
    async def get_capabilities() -> List[Capability]
    async def health_check() -> bool
    async def shutdown() -> None
```

#### **2. Agent Types & Specialization**

| Agent Type | Framework | Use Case | Status |
|------------|-----------|----------|--------|
| **Ollama Local** | Ollama | Fast inline suggestions, local inference | ✅ Active |
| **LangChain** | LangChain | RAG, document Q&A, chains | ✅ Active |
| **CrewAI** | CrewAI | Role-based collaboration (PM, Dev, QA) | ✅ Active |
| **SuperAGI** | SuperAGI | Autonomous goal-driven execution | ✅ Complete |
| **AutoGPT** | AutoGPT | Research, multi-step planning | ✅ Complete |

#### **3. Task Routing Logic**
```python
# Orchestrator decides which agent(s) to use based on:
- Task type (refactor, explain, generate, debug)
- Code context (language, complexity, file size)
- Agent capabilities (code_gen, research, testing)
- Performance metrics (latency, acceptance rate)
- User preferences
```

---

## 🚀 Local Inference & Caching Strategy

### **1. Model Selection (Ollama)**
```yaml
Tier 1 (Ultra-fast): LLaMA 3.2 3B
  - Inline suggestions (<200ms)
  - Simple completions
  - Syntax fixes

Tier 2 (Balanced): CodeLLaMA 7B / Mistral 7B
  - Code generation (500-1000ms)
  - Refactoring
  - Explanations

Tier 3 (Complex): DeepSeek Coder 33B (optional)
  - Architecture design
  - Complex debugging
  - Research tasks
```

### **2. Multi-Tier Caching**
```python
L1 Cache (Memory): LRU cache for recent suggestions
  - 100 most recent code contexts
  - <10ms lookup
  - Cleared on file change

L2 Cache (Redis): Session-level cache
  - Similar code patterns (embeddings-based)
  - 5-minute TTL
  - Shared across workspace

L3 Cache (ChromaDB): Long-term vector cache
  - Code embeddings for similarity search
  - Persistent across sessions
  - Used for RAG and pattern matching
```

### **3. Predictive Caching (ML-Driven)**
```python
# Analyze user patterns to pre-cache:
- Peak coding hours (9-10am, 2-3pm)
- Frequently used languages (Python, TypeScript)
- Common actions (refactor, explain)
- Pre-warm models during idle time
```

---

## 🔌 Plugin & Context Management

### **1. Context Collection**
```typescript
// IDE Extension collects:
interface CodeContext {
  file_path: string;
  language: string;
  code: string;              // Full file content
  selected_text?: string;    // User selection
  cursor_position: Position;
  surrounding_code: string;  // ±50 lines
  imports: string[];         // File dependencies
  git_diff?: string;         // Recent changes
}
```

### **2. Context Enrichment (Backend)**
```python
# Backend enriches with:
- AST analysis (syntax tree)
- Symbol resolution (functions, classes)
- Type information (LSP integration)
- Related files (imports, references)
- Historical patterns (previous suggestions)
- Vector embeddings (semantic similarity)
```

### **3. Plugin System**
```python
# Modular plugin architecture:
plugins/
  ├── code_analysis/      # AST, linting, complexity
  ├── vector_search/      # ChromaDB embeddings
  ├── git_integration/    # Diff analysis, blame
  ├── test_generation/    # Auto-generate tests
  └── documentation/      # Auto-generate docs
```

---

## 🛡️ Safety & Provenance Logging

### **1. Safety Mechanisms**
```python
# Pre-execution validation:
- Syntax checking (no broken code)
- Security scanning (no hardcoded secrets)
- Dependency validation (no malicious imports)
- Sandboxed execution (isolated environment)

# Post-execution validation:
- Code review (automated checks)
- Test execution (verify correctness)
- Rollback capability (undo changes)
```

### **2. Provenance Logging**
```python
# Every suggestion tracked:
{
  "suggestion_id": "uuid",
  "timestamp": "2025-10-13T10:30:00Z",
  "agent_name": "SuperAGI Code Agent",
  "model": "gpt-4",
  "task_type": "refactor",
  "context_hash": "sha256...",
  "code_before": "...",
  "code_after": "...",
  "user_action": "accepted",
  "confidence": 0.85,
  "reasoning": "...",
  "execution_time_ms": 1200
}
```

### **3. Audit Trail**
```python
# Stored in:
- Local SQLite (developer machine)
- Analytics service (aggregated metrics)
- Optional enterprise logging (compliance)

# Used for:
- Debugging (why did agent suggest X?)
- Learning (improve future suggestions)
- Compliance (code review audit)
- Attribution (Herman Swanepoel - Project Creator)
```

---

## 📊 Current Sprint Status

**Phase:** Beta Deployment (Week 3-8)

### **Completed:**
- ✅ Core agent adapters (Ollama, LangChain, CrewAI)
- ✅ SuperAGI & AutoGPT integration
- ✅ Analytics dashboard with metrics
- ✅ WebSocket real-time communication
- ✅ Multi-language support

### **In Progress (HIGH Priority):**
- 🚧 Accessibility fixes (WCAG compliance)
- 🚧 Exponential backoff for adapters
- 🚧 Code refactoring (shared utilities)
- 🚧 Test coverage for adapters

### **Next (MEDIUM Priority):**
- 📋 Predictive caching implementation
- 📋 LLM response caching
- 📋 Error handling standardization
- 📋 Comprehensive type hints

---

## 🔑 Key Differentiators

1. **Local-First:** Privacy-focused, no cloud dependency
2. **Multi-Agent:** Best agent for each task (not one-size-fits-all)
3. **Enterprise-Ready:** SuperAGI, AutoGPT, CrewAI integration
4. **ML-Optimized:** Predictive caching, pattern learning
5. **Production-Grade:** Comprehensive logging, error handling, testing

---

## 📁 Project Structure

```
aura-ia/
├── extension/                    # VS Code Extension
│   ├── src/
│   │   ├── extension.ts         # Main extension entry
│   │   ├── providers/           # Code completion, actions
│   │   ├── panels/              # WebView panels (chat, analytics)
│   │   ├── services/            # Analytics, WebSocket client
│   │   └── utils/               # Helpers, formatters
│   └── package.json
│
├── backend/                      # Python FastAPI Backend
│   ├── src/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── adapters/            # Agent adapters
│   │   │   ├── base_adapter.py
│   │   │   ├── adapter_utils.py # Shared utilities ✅
│   │   │   ├── ollama_adapter.py
│   │   │   ├── langchain_adapter.py
│   │   │   ├── crewai_adapter.py
│   │   │   ├── superagi_adapter.py ✅
│   │   │   └── autogpt_adapter.py ✅
│   │   ├── services/            # Business logic
│   │   │   ├── orchestrator.py  # Agent routing
│   │   │   ├── context_manager.py
│   │   │   └── analytics_service.py
│   │   ├── models/              # Data models
│   │   ├── api/                 # REST/WebSocket endpoints
│   │   └── config/              # Configuration
│   └── requirements.txt
│
├── .kiro/                        # Kiro IDE configuration
│   ├── steering/                # Development guidelines
│   └── specs/                   # Feature specifications
│
├── docs/                         # Documentation
├── tests/                        # Test suites
├── PROJECT_ARCHITECTURE.md       # This file
├── DEVELOPER_GUIDE.md           # Developer documentation
└── README.md                    # Project overview
```

---

## 🚀 Getting Started

### **Prerequisites**
```bash
# Install Ollama (local LLM runtime)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3.2:3b
ollama pull codellama:7b
ollama pull mistral:7b

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Install Node dependencies
cd extension
npm install
```

### **Running the System**
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
cd backend
uvicorn src.main:app --reload --port 8000

# Terminal 3: Start Extension (VS Code)
# Press F5 in VS Code to launch Extension Development Host
```

---

## 🔧 Configuration

### **Backend Configuration**
```python
# backend/src/config/settings.py
OLLAMA_BASE_URL = "http://localhost:11434"
REDIS_URL = "redis://localhost:6379"
CHROMA_PERSIST_DIR = "./chroma_db"

# Agent timeouts
INLINE_SUGGESTION_TIMEOUT = 2000  # ms
CODE_GENERATION_TIMEOUT = 10000   # ms
RESEARCH_TIMEOUT = 30000          # ms
```

### **Extension Configuration**
```json
// .vscode/settings.json
{
  "auraIA.backend.url": "http://localhost:8000",
  "auraIA.inline.enabled": true,
  "auraIA.inline.debounceMs": 300,
  "auraIA.agents.preferred": ["ollama", "langchain"],
  "auraIA.analytics.enabled": true
}
```

---

## 🧪 Testing Strategy

### **Unit Tests**
```bash
# Backend
pytest backend/tests/unit/

# Extension
npm test
```

### **Integration Tests**
```bash
# Test agent adapters
pytest backend/tests/integration/test_adapters.py

# Test orchestration
pytest backend/tests/integration/test_orchestrator.py
```

### **E2E Tests**
```bash
# VS Code extension tests
npm run test:e2e
```

---

## 📈 Performance Metrics

### **Target Latencies**
- Inline suggestions: <200ms (p95)
- Code actions: <1000ms (p95)
- Agent discussion: <3000ms (p95)
- Analytics refresh: <500ms (p95)

### **Resource Usage**
- Memory: <500MB (extension + backend)
- CPU: <20% (idle), <60% (active inference)
- Disk: <2GB (models + cache)

---

## 🔐 Security Considerations

### **Data Privacy**
- All inference runs locally (no cloud calls)
- Code never leaves developer machine
- Optional telemetry (opt-in only)
- Encrypted cache storage

### **Code Safety**
- Syntax validation before application
- Sandboxed execution environment
- User confirmation for destructive changes
- Rollback capability (undo stack)

---

## 🛣️ Roadmap

### **Q1 2025 - Beta Release**
- ✅ Core multi-agent system
- ✅ SuperAGI & AutoGPT integration
- 🚧 Accessibility compliance
- 🚧 Comprehensive testing

### **Q2 2025 - Production Release**
- 📋 Enterprise SSO integration
- 📋 Team collaboration features
- 📋 Custom agent training
- 📋 Performance optimization

### **Q3 2025 - Advanced Features**
- 📋 Multi-IDE support (JetBrains, Vim)
- 📋 Mobile companion app
- 📋 Cloud sync (optional)
- 📋 Marketplace for custom agents

---

## 🤝 Contributing

See [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) for detailed contribution guidelines.

---

## 📄 License

Proprietary - Herman Swanepoel

---

## 👤 Author

**Herman Swanepoel** - *Project Creator*

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-13  
**Project Creator:** Herman Swanepoel
