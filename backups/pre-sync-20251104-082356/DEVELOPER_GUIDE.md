# Developer Guide - Enterprise AI Agents Integration

**Project Creator:** Herman Swanepoel  
**Version:** 1.0.0

This guide provides comprehensive information for developers who want to contribute to or extend the Enterprise AI Agents Integration system.

---

## 📚 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Extension Development](#extension-development)
4. [Backend Development](#backend-development)
5. [Creating Custom Agents](#creating-custom-agents)
6. [Adding Framework Adapters](#adding-framework-adapters)
7. [Testing](#testing)
8. [Debugging](#debugging)
9. [Best Practices](#best-practices)
10. [API Reference](#api-reference)

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     VS Code Extension                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Providers   │  │   Panels     │  │   Services   │     │
│  │  - Inline    │  │  - Discussion│  │  - WebSocket │     │
│  │  - Actions   │  │  - Analytics │  │  - Workspace │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                    WebSocket Connection
                            │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Adapters   │  │    Agents    │  │   Services   │     │
│  │  - CrewAI    │  │  - Refactor  │  │  - LLM       │     │
│  │  - SuperAGI  │  │  - Bug       │  │  - Embeddings│     │
│  │  - AutoGPT   │  │  - Doc       │  │  - Memory    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
            ┌───────▼──────┐  ┌────▼─────┐
            │   Ollama     │  │  Redis   │
            │   (LLM)      │  │ ChromaDB │
            └──────────────┘  └──────────┘
```

### Data Flow

1. **User Action** → VS Code Extension
2. **Extension** → WebSocket → Backend
3. **Backend** → Meta-Orchestrator → Agent Selection
4. **Agent** → LLM/Tools → Generate Response
5. **Response** → WebSocket → Extension
6. **Extension** → Display to User

---

## 🛠️ Development Setup

### Prerequisites

```bash
# Required
- Node.js 16.x or higher
- Python 3.10 or higher
- Git
- VS Code 1.85.0+

# Optional
- Docker & Docker Compose
- Ollama (for local LLM)
```

### Initial Setup

```bash
# Clone repository
git clone https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents.git
cd IDE-Extension-for-local-AI-Agents

# Install extension dependencies
cd extension
npm install
npm run compile

# Install backend dependencies
cd ../backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Start services
docker-compose up -d  # Redis, ChromaDB
python -m uvicorn src.main:app --reload
```

### Running multiple backend instances (multi-agent dev)

For parallel development and isolation testing, run several Uvicorn instances bound to different ports.

- VS Code tasks:
  - `Start Multi-Agent Backends (3x)` — starts instances on 8001/8002/8003 with `APP_INSTANCE` set per process
  - Individual tasks exist for 8001, 8002, 8003
- PowerShell helper (Windows):

```powershell
./start-multi-agents.ps1 -Count 3 -BasePort 8001 -BindHost 127.0.0.1
```

Flags: `-Count`, `-BasePort`, `-BindHost`, and `-NoReload` (to disable hot reload).

### CI pipelines and gates

- Type checking runs on backend path changes with pip caching.
- CI splits:
  - Linting & config checks (Black, Flake8, yamllint, Prometheus promtool)
  - Tests with coverage and a gate (`--cov-fail-under=60`)
  - Docker build depends on successful tests

### Repository housekeeping

- The `work/refactor` subtree has been removed to keep the repository clean and reduce pre-commit churn.
- Pre-commit hooks are scoped to `backend/**` to focus on actionable signals.

### Environment Variables

Create `backend/.env`:

```env
# Development
DEBUG=true
LOG_LEVEL=DEBUG

# LLM
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b

# Database
REDIS_URL=redis://localhost:6379
CHROMADB_PATH=./data/chromadb

# Optional Cloud LLMs
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

---

## 🔌 Extension Development

### Project Structure

```
extension/
├── src/
│   ├── extension.ts              # Entry point
│   ├── providers/                # VS Code providers
│   ├── panels/                   # Webview panels
│   ├── services/                 # Core services
│   └── ui/                       # UI components
├── package.json                  # Extension manifest
└── tsconfig.json                 # TypeScript config
```

### Creating a New Provider

```typescript
// extension/src/providers/MyProvider.ts
import * as vscode from "vscode";

export class MyProvider implements vscode.SomeProvider {
  constructor(private wsClient: WebSocketClient) {}

  async provideSomething(document: vscode.TextDocument, position: vscode.Position): Promise<vscode.Something[]> {
    // Your implementation
    const response = await this.wsClient.sendWithResponse("my_action", {
      document,
      position,
    });

    return this.convertResponse(response);
  }
}
```

### Registering Commands

```typescript
// In extension.ts
const myCommand = vscode.commands.registerCommand("enterpriseAI.myCommand", async () => {
  // Command implementation
});

context.subscriptions.push(myCommand);
```

### Creating Webview Panels

```typescript
export class MyPanel {
  public static currentPanel: MyPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;

  public static createOrShow(extensionUri: vscode.Uri) {
    // Implementation
  }

  private _getHtmlForWebview(): string {
    return `<!DOCTYPE html>
        <html>
            <!-- Your HTML -->
        </html>`;
  }
}
```

---

## 🐍 Backend Development

### Project Structure

```
backend/
├── src/
│   ├── main.py                   # FastAPI app
│   ├── adapters/                 # Framework adapters
│   ├── agents/                   # Specialized agents
│   ├── services/                 # Core services
│   └── models/                   # Data models
├── tests/                        # Test suite
└── requirements.txt              # Dependencies
```

### Creating a WebSocket Endpoint

```python
# backend/src/main.py
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str
):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            # Handle message
            response = await handle_message(data)

            await websocket.send_json(response)
    except WebSocketDisconnect:
        # Cleanup
        pass
```

### Creating REST Endpoints

```python
@app.post("/api/analyze")
async def analyze_code(request: AnalyzeRequest):
    """Analyze code and return suggestions"""

    # Get agent
    agent = get_agent(request.agent_type)

    # Execute
    result = await agent.analyze(request.code)

    return result
```

### Configuring Cloud LLM Providers

The backend can defer to OpenAI or Anthropic when Ollama is unavailable or when a cloud-only model is requested. Keep these prerequisites in mind before enabling the fallback:

- Install the optional SDKs in the backend virtual environment:

  ```bash
  pip install openai anthropic
  ```

- Set the relevant API keys in `backend/.env` (lines are present but empty by default):

  ```env
  OPENAI_API_KEY=sk-...
  ANTHROPIC_API_KEY=...
  ```

- When instantiating `LLMManager`, pass `allow_cloud=True` and the desired `LLMProvider` (`openai` or `anthropic`). Without this flag, any remote execution attempt raises `LLMError`.
- The manager runs all prompts through `PrivacyManager` before dispatching them to the cloud. Inputs containing email addresses, phone numbers, secrets, or token-like substrings are blocked and logged. Sanitised prompts replace sensitive values with `[REDACTED]` markers.
- Responses are cached under the selected provider so Ollama and cloud completions maintain independent cache entries.

#### Verifying Cloud Connectivity

With credentials in place, you can validate the integration manually:

1. Run the targeted unit tests to ensure local mocking still succeeds:

   ```bash
   pytest backend/tests/unit/test_services_critical.py -k cloud -v
   ```

2. Exercise the real API with a short Python snippet (replace `provider` and `prompt` as needed):

   ```python
   import asyncio
   import os

   from src.services.llm_manager import LLMManager, LLMProvider


   async def main() -> None:
       manager = LLMManager(
           provider=LLMProvider.OPENAI,
           model="gpt-4o-mini",
           api_key=os.environ["OPENAI_API_KEY"],
           allow_cloud=True,
       )

       print(
           await manager.generate(
               "Say hello from the integration test.",
               temperature=0.2,
               max_tokens=60,
           )
       )


   asyncio.run(main())
   ```

3. The `health_check` coroutine reaches out to the cloud provider client. Invoke it from a REPL or sanity-check it inside a monitoring task to confirm the SDK is correctly initialised.

4. Example output from the live validation run (gpt-4o-mini, 2025-10-19):

   ```text
   The cloud fallback test has been successfully completed, confirming that all systems functioned as intended during the transition. We are now fully operational with the backup infrastructure in place.
   ```

> **Note:** Anthropic parity is optional. If your deployment does not provision `ANTHROPIC_API_KEY`, the Claude provider will remain inactive and `LLMManager` will continue operating with Ollama/OpenAI only. To enable Anthropic later, install the `anthropic` package, export the key, and rerun the smoke snippet above using `LLMProvider.ANTHROPIC`.

---

## 🤖 Creating Custom Agents

### Agent Interface

All agents must implement the base interface:

```python
from src.models import Task, AgentResponse, CodeContext

class MyCustomAgent:
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.name = "My Custom Agent"

    async def analyze_code(
        self,
        task: Task,
        context: CodeContext
    ) -> AgentResponse:
        """
        Analyze code and return suggestions

        Args:
            task: Task to execute
            context: Code context

        Returns:
            AgentResponse with suggestions
        """
        # Your implementation
        suggestions = await self._generate_suggestions(context)

        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            suggestions=suggestions,
            confidence=0.85,
            reasoning="Generated by custom agent"
        )

    async def _generate_suggestions(
        self,
        context: CodeContext
    ) -> List[Suggestion]:
        # Implementation
        pass
```

### Registering Custom Agent

```python
# In orchestrator.py
from src.agents.my_custom_agent import MyCustomAgent

class MetaOrchestrator:
    def __init__(self):
        self.agents = {
            "custom": MyCustomAgent(llm_manager),
            # ... other agents
        }
```

---

## 🔌 Adding Framework Adapters

### Adapter Interface

```python
from src.adapters.base_adapter import AgentAdapter, AgentConfig

class MyFrameworkAdapter(AgentAdapter):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        # Your initialization

    async def initialize(self) -> None:
        """Initialize the adapter"""
        # Setup connection, load models, etc.
        self.is_initialized = True

    async def execute_task(
        self,
        task: Task,
        context: CodeContext
    ) -> AgentResponse:
        """Execute task using the framework"""
        # Your implementation
        pass

    async def get_capabilities(self) -> List[Capability]:
        """Return supported capabilities"""
        return self.config.capabilities

    async def health_check(self) -> bool:
        """Check if adapter is healthy"""
        return self.is_initialized

    async def shutdown(self) -> None:
        """Cleanup resources"""
        await super().shutdown()
```

### Registering Adapter

```python
# In main.py or orchestrator
from src.adapters.my_framework_adapter import MyFrameworkAdapter

adapter = MyFrameworkAdapter(config)
await adapter.initialize()

adapter_registry.register("my_framework", adapter)
```

---

## 🧪 Testing

### Extension Tests

```typescript
// extension/src/test/suite/myProvider.test.ts
import * as assert from "assert";
import * as vscode from "vscode";
import { MyProvider } from "../../providers/MyProvider";

suite("MyProvider Test Suite", () => {
  test("Should provide suggestions", async () => {
    const provider = new MyProvider(mockWsClient);
    const result = await provider.provideSomething(mockDocument, mockPosition);

    assert.ok(result.length > 0);
  });
});
```

### Backend Tests

```python
# backend/tests/test_agents.py
import pytest
from src.agents.my_custom_agent import MyCustomAgent

@pytest.mark.asyncio
async def test_custom_agent():
    agent = MyCustomAgent(mock_llm_manager)

    result = await agent.analyze_code(mock_task, mock_context)

    assert result.suggestions
    assert result.confidence > 0.5
```

### Running Tests

```bash
# Extension tests
cd extension
npm test

# Backend tests
cd backend
pytest

# With coverage
pytest --cov=src tests/

# Specific test
pytest tests/test_agents.py::test_custom_agent
```

---

## 🐛 Debugging

### Extension Debugging

1. Open extension folder in VS Code
2. Press `F5` to start debugging
3. New VS Code window opens with extension loaded
4. Set breakpoints in TypeScript files
5. Use Debug Console for inspection

### Backend Debugging

```python
# Add to code
import pdb; pdb.set_trace()

# Or use VS Code debugger
# Create .vscode/launch.json:
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.main:app",
                "--reload"
            ]
        }
    ]
}
```

### WebSocket Debugging

```typescript
// Enable verbose logging
wsClient.on("message", (data) => {
  console.log("Received:", data);
});

wsClient.on("error", (error) => {
  console.error("WebSocket error:", error);
});
```

---

## 📋 Best Practices

### Code Style

**TypeScript:**

- Use ESLint configuration
- Follow VS Code extension guidelines
- Use async/await for promises
- Add JSDoc comments

**Python:**

- Follow PEP 8
- Use type hints
- Add docstrings (Google style)
- Use Black for formatting

### Error Handling

```typescript
// Extension
try {
  const result = await riskyOperation();
  return result;
} catch (error) {
  vscode.window.showErrorMessage(`Operation failed: ${error}`);
  console.error("Detailed error:", error);
  return null;
}
```

```python
# Backend
try:
    result = await risky_operation()
    return result
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### Performance

- Cache expensive operations
- Use debouncing for user input
- Implement request deduplication
- Monitor memory usage
- Profile slow operations

### Security

- Sanitize user input
- Validate all data
- Use environment variables for secrets
- Implement rate limiting
- Follow least privilege principle

---

## 📖 API Reference

### WebSocket Messages

**Client → Server:**

```typescript
{
    "type": "inline_suggestion",
    "data": {
        "file_path": string,
        "language": string,
        "cursor_position": { line: number, character: number },
        "surrounding_code": string
    }
}
```

**Server → Client:**

```typescript
{
    "type": "agent_response",
    "data": {
        "task_id": string,
        "agent_name": string,
        "suggestions": Suggestion[],
        "confidence": number,
        "reasoning": string
    }
}
```

### REST Endpoints

#### POST /api/analyze

```python
Request:
{
    "code": str,
    "language": str,
    "agent_type": str
}

Response:
{
    "suggestions": List[Suggestion],
    "confidence": float
}
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Commit Message Format

```text
type(scope): subject

body

footer
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

---

**Project Creator:** Herman Swanepoel  
**Last Updated:** 2025-10-13  
**Version:** 1.0.0
