# Enterprise AI Agents Integration for VS Code

**Project Creator:** Herman Swanepoel  
**Version:** 1.0.0  
**Status:** Production Ready

A comprehensive multi-agent AI coding assistant with privacy-first local operations, featuring specialized agents for code generation, refactoring, bug detection, documentation, and testing.

---

## 🌟 Features

### Multi-Agent Collaboration
- **CrewAI Integration** - Collaborative documentation and test generation
- **SuperAGI Integration** - Autonomous code generation with tool support
- **AutoGPT Integration** - Deep research and complex analysis
- **Specialized Agents** - Refactor, Bug, Doc, and Test agents

### AI-Powered Code Actions
- **8+ Action Types** - Extract function, simplify, optimize, fix diagnostics
- **Preview Before Apply** - See changes before committing
- **One-Click Rollback** - Undo any AI-generated changes
- **Confidence Scoring** - Know how reliable each suggestion is

### Inline Suggestions
- **Real-Time Completions** - <200ms response time with caching
- **LRU Cache** - Intelligent caching with request deduplication
- **Acceptance Tracking** - Learn from your preferences
- **Alternative Suggestions** - Get multiple options

### Security & Bug Detection
- **6+ Security Patterns** - SQL injection, XSS, hardcoded secrets, etc.
- **Static Analysis** - Language-specific checks
- **LLM-Powered Detection** - Deep code analysis
- **Severity Categorization** - Critical/High/Medium/Low

### Documentation Generation
- **Python Docstrings** - Google-style automatic generation
- **JSDoc Comments** - JavaScript/TypeScript support
- **README Templates** - Project documentation
- **API Documentation** - Comprehensive API docs

### Productivity Analytics
- **Acceptance Rates** - Track suggestion effectiveness
- **Agent Metrics** - Monitor agent performance
- **Workflow Patterns** - Identify productivity trends
- **Interactive Dashboard** - Visualize your data with charts

### Workspace Management
- **Multi-Workspace Support** - Switch between projects seamlessly
- **State Preservation** - Restore open files and cursor positions
- **Per-Workspace Settings** - Configure agents per project
- **Quick Switcher** - Fast workspace navigation

### Privacy First
- **Local LLM Support** - Ollama integration for offline operation
- **Cloud Fallback** - Optional OpenAI/Anthropic with privacy controls
- **No Data Collection** - All analytics stored locally
- **Opt-Out Mechanism** - Full control over telemetry

---

## 📦 Installation

### Prerequisites
- **VS Code** 1.85.0 or higher
- **Python** 3.10 or higher
- **Node.js** 16.x or higher
- **Ollama** (for local LLM) or API keys for cloud providers

### Quick Start

1. **Install the Extension**
   ```bash
   # From VS Code Marketplace (coming soon)
   # Or install from VSIX
   code --install-extension enterprise-ai-agents-1.0.0.vsix
   ```

2. **Install Backend Dependencies**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Start Backend Services**
   ```bash
   # Start with Docker Compose (recommended)
   docker-compose up -d

   # Or start manually
   cd backend
   python -m uvicorn src.main:app --reload
   ```

4. **Configure Extension**
   - Open VS Code Settings
   - Search for "Enterprise AI"
   - Set backend URL (default: `http://localhost:8000`)
   - Configure LLM provider (Ollama/Cloud)

---

## 🚀 Usage

### Quick Actions

**Keyboard Shortcuts:**
- `Ctrl+Shift+M` - Toggle Offline/Online Mode
- `Ctrl+Shift+T` - Generate Tests
- `Ctrl+Shift+R` - Refactor Selection
- `Ctrl+Shift+E` - Explain Code
- `Ctrl+Shift+S` - Security Scan
- `Ctrl+Shift+D` - Generate Documentation
- `Ctrl+Shift+Alt+E` - Extract Function
- `Ctrl+Shift+Alt+S` - Simplify Code
- `Ctrl+Shift+Alt+O` - Optimize Code
- `Ctrl+Shift+Alt+Z` - Rollback Last Action
- `Ctrl+Shift+Alt+Q` - Quick Actions Menu

### Command Palette

Press `Ctrl+Shift+P` and type "Enterprise AI" to see all available commands:

- **Enterprise AI: Toggle Offline/Online Mode** - Switch between local and cloud LLMs
- **Enterprise AI: Generate Tests** - Create unit tests for current file
- **Enterprise AI: Refactor Selection** - Get refactoring suggestions
- **Enterprise AI: Find Security Issues** - Scan for vulnerabilities
- **Enterprise AI: Generate Documentation** - Create docs for your code
- **Enterprise AI: Start Agent Discussion** - Collaborate with multiple agents
- **Enterprise AI: View Analytics Dashboard** - See productivity insights
- **Enterprise AI: Switch Workspace** - Change to different project
- **Enterprise AI: Rollback Last Action** - Undo AI changes

### Inline Suggestions

1. Start typing code
2. Wait 200ms for suggestions to appear
3. Press `Tab` to accept or `Esc` to dismiss
4. Use `Ctrl+Shift+Alt+R` for alternative suggestions

### Code Actions

1. Select code or place cursor on diagnostic
2. Click the lightbulb 💡 or press `Ctrl+.`
3. Choose an AI action from the menu
4. Preview changes in modal dialog
5. Click "Apply" to accept or "Cancel" to dismiss

### Agent Discussion

1. Select code you want to discuss
2. Press `Ctrl+Shift+P` → "Start Agent Discussion"
3. Enter discussion title
4. Ask questions or request input
5. Review agent responses and suggestions
6. Approve/reject individual suggestions

### Analytics Dashboard

1. Press `Ctrl+Shift+P` → "View Analytics Dashboard"
2. View charts and metrics
3. Export data as JSON
4. Clear data if needed

---

## ⚙️ Configuration

### Extension Settings

```json
{
  // Backend Configuration
  "enterpriseAI.backend.url": "http://localhost:8000",
  
  // Privacy Settings
  "enterpriseAI.privacy.allowCloud": false,
  "enterpriseAI.privacy.allowTelemetry": false,
  
  // LLM Configuration
  "enterpriseAI.llm.provider": "ollama",
  "enterpriseAI.llm.model": "codellama:7b",
  
  // Suggestions
  "enterpriseAI.suggestions.autoTrigger": true,
  "enterpriseAI.suggestions.debounceMs": 200,
  
  // Accessibility
  "enterpriseAI.accessibility.screenReaderEnabled": false,
  "enterpriseAI.accessibility.highContrastMode": false,
  "enterpriseAI.accessibility.keyboardNavigationEnabled": true
}
```

### Workspace Configuration

Create `.vscode/ai-agents-workspace.json` in your project:

```json
{
  "name": "My Project",
  "description": "Web application with React and Node.js",
  "strengths": ["frontend", "api", "testing"],
  "agentSettings": {
    "Refactor Agent": {
      "enabled": true,
      "priority": 1
    },
    "Bug Agent": {
      "enabled": true,
      "priority": 2
    },
    "Doc Agent": {
      "enabled": false
    }
  }
}
```

### Backend Configuration

Edit `backend/.env`:

```env
# LLM Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b

# Cloud LLM (optional)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Database
REDIS_URL=redis://localhost:6379
CHROMADB_PATH=./data/chromadb

# Server
HOST=0.0.0.0
PORT=8000
```

---

## 🏗️ Architecture

### Frontend (VS Code Extension)
```
extension/
├── src/
│   ├── extension.ts              # Main entry point
│   ├── providers/
│   │   ├── InlineSuggestionProvider.ts
│   │   └── CodeActionProvider.ts
│   ├── panels/
│   │   ├── AgentDiscussionPanel.ts
│   │   └── AnalyticsDashboardPanel.ts
│   ├── services/
│   │   ├── WebSocketClient.ts
│   │   ├── WorkspaceManager.ts
│   │   ├── AnalyticsService.ts
│   │   └── ModeToggle.ts
│   └── ui/
│       ├── StatusBarManager.ts
│       └── AgentStatusTreeProvider.ts
```

### Backend (Python FastAPI)
```
backend/
├── src/
│   ├── main.py                   # FastAPI app
│   ├── adapters/
│   │   ├── crewai_adapter.py
│   │   ├── superagi_adapter.py
│   │   └── autogpt_adapter.py
│   ├── agents/
│   │   ├── refactor_agent.py
│   │   ├── bug_agent.py
│   │   ├── doc_agent.py
│   │   └── orchestrator.py
│   └── services/
│       ├── llm_manager.py
│       ├── embeddings_service.py
│       └── memory_service.py
```

---

## 🤖 Agents

### Refactor Agent
- Code smell detection
- Design pattern suggestions
- Performance optimization
- Maintainability improvements

### Bug Agent
- Security vulnerability detection
- Static code analysis
- LLM-powered bug detection
- Fix generation with explanations

### Doc Agent
- Python docstring generation
- JSDoc comment generation
- README template creation
- API documentation

### Test Agent (via CrewAI)
- Unit test generation
- Integration test scaffolding
- Edge case identification
- Test coverage analysis

### CrewAI Agents
- Collaborative multi-agent execution
- Doc and Test specialists
- Sequential workflow processing

### SuperAGI Agents
- Autonomous code generation
- Tool-based execution
- Goal-driven development

### AutoGPT Agents
- Deep research and analysis
- Complex multi-step tasks
- Memory-based execution

---

## 📊 Analytics

### Metrics Tracked
- Suggestion acceptance/rejection rates
- Agent effectiveness scores
- Language usage distribution
- Hourly activity patterns
- Workflow insights

### Privacy
- All data stored locally
- 90-day retention policy
- Opt-out available
- No external transmission

---

## 🔒 Security

### Security Patterns Detected
- SQL Injection
- Command Injection
- Hardcoded Secrets
- XSS Vulnerabilities
- Path Traversal
- Insecure Random

### Privacy Controls
- Local-first operation
- Optional cloud fallback
- Data sanitization
- Secrets management
- No telemetry by default

---

## 🧪 Testing

```bash
# Run extension tests
cd extension
npm test

# Run backend tests
cd backend
pytest

# Run integration tests
pytest tests/integration/
```

---

## 📝 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents.git
cd IDE-Extension-for-local-AI-Agents

# Install extension dependencies
cd extension
npm install

# Install backend dependencies
cd ../backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start development
npm run watch  # In extension directory
python -m uvicorn src.main:app --reload  # In backend directory
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **CrewAI** - Multi-agent collaboration framework
- **SuperAGI** - Autonomous agent framework
- **AutoGPT** - Research and analysis framework
- **Ollama** - Local LLM runtime
- **VS Code** - Extension platform

---

## 📞 Support

- **Issues:** https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents/issues
- **Discussions:** https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents/discussions
- **Documentation:** https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents/wiki

---

## 🗺️ Roadmap

- [ ] Voice command integration
- [ ] Suggestion comparison UI
- [ ] Dependency management
- [ ] VS Code Marketplace publication
- [ ] Additional language support
- [ ] Plugin system for custom agents

---

**Project Creator:** Herman Swanepoel  
**Last Updated:** 2025-10-13  
**Version:** 1.0.0

