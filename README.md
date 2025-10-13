# Enterprise AI Agents Integration

**A privacy-first, multi-agent AI coding assistant for VS Code**

## Author

**Herman Swanepoel** - *Project Creator*

## Overview

Enterprise AI Agents Integration is a VS Code extension that provides Copilot-style coding assistance through multiple specialized AI agents. It prioritizes privacy with local-first operations while offering optional cloud enhancements.

## Key Features

- 🔒 **Privacy-First**: All operations run locally by default
- 🤖 **Multi-Agent System**: 6 specialized AI agents (Refactor, Doc, Bug, Test, Research, Orchestrator)
- 💠 **Mode Toggle**: Easy switch between offline (local) and online (cloud) modes with neon visual indicators
- ⚡ **Real-time Suggestions**: Inline code suggestions as you type (<200ms)
- � ***Automated Testing**: AI-generated unit and integration tests
- � ***Security Analysis**: Real-time vulnerability detection
- 💬 **Agent Discussion**: Multi-agent collaboration panel
- 📊 **Analytics Dashboard**: Track productivity and agent effectiveness

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- VS Code 1.85+
- Git

### Installation

#### Windows

```powershell
# Run automated setup
.\setup.ps1

# Activate backend
cd backend
.\venv\Scripts\Activate.ps1

# Start backend service
python src/main.py
```

#### Manual Setup

See [PROJECT_SETUP.md](PROJECT_SETUP.md) for detailed instructions.

## Project Structure

```
enterprise-ai-agents/
├── extension/              # VS Code Extension (TypeScript)
├── backend/                # Python Backend Service
│   └── venv/              # Virtual Environment
├── frameworks/             # Agent Frameworks (CrewAI, SuperAGI, AutoGPT)
├── data/                   # Local data storage
├── setup.ps1              # Windows setup script
└── docker-compose.yml     # Docker services
```

## Architecture

- **Frontend**: TypeScript VS Code Extension
- **Backend**: Python FastAPI service
- **Agents**: CrewAI, SuperAGI, AutoGPT integration
- **LLM**: Ollama (local) with optional cloud fallback
- **Vector DB**: ChromaDB for code embeddings
- **Session Store**: Redis for memory management

## Mode Toggle

Switch between offline and online modes with a prominent visual toggle:

- **💠 LOCAL MODE** (Neon Blue): Fully local operation, maximum privacy
- **☁️ CLOUD MODE** (Neon Green): Cloud LLM fallback enabled

## Documentation

- [Project Setup Guide](PROJECT_SETUP.md)
- [Requirements](.kiro/specs/enterprise-ai-agents-integration/requirements.md)
- [Design Document](.kiro/specs/enterprise-ai-agents-integration/design.md)
- [Implementation Tasks](.kiro/specs/enterprise-ai-agents-integration/tasks.md)

## Development

### Backend Development

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python src/main.py
```

### Extension Development

1. Open `extension/` folder in VS Code
2. Press `F5` to start debugging
3. A new VS Code window will open with the extension loaded

### Running Tests

```powershell
# Backend tests
cd backend
.\venv\Scripts\Activate.ps1
pytest tests/ -v

# Extension tests
cd extension
npm test
```

## Configuration

Edit `backend/.env` to configure:

- Backend host and port
- LLM provider and model
- Privacy settings
- Cloud API keys (optional)

## Contributing

This is a personal project by Herman Swanepoel. Contributions, issues, and feature requests are welcome!

## License

[Your License Here]

## Acknowledgments

- CrewAI for multi-agent collaboration
- SuperAGI for autonomous agent capabilities
- AutoGPT for research and planning
- Ollama for local LLM inference

---

**Project Creator:** Herman Swanepoel  
**Version:** 1.0.0  
**Last Updated:** 2025-01-13
