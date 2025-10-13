# Enterprise AI Agents Integration - Project Setup Guide

**Project Creator:** Herman Swanepoel  
**Version:** 1.0  
**Last Updated:** 2025-01-13

---

## Overview

This project integrates multiple AI agent frameworks (AutoGPT, CrewAI, SuperAGI) into a unified VS Code extension with privacy-first local operations and optional cloud enhancements.

## Prerequisites

- **Python 3.11+** - Required for backend service
- **Node.js 18+** - Required for VS Code extension
- **Git** - For version control
- **VS Code** - For extension development
- **Ollama** (optional) - For local LLM inference

## Quick Start

### Windows

```powershell
# Clone or navigate to project directory
cd enterprise-ai-agents

# Run automated setup
.\setup.ps1

# Activate backend environment
cd backend
.\venv\Scripts\Activate.ps1

# Start backend service
python src/main.py
```

### Linux/Mac

```bash
# Clone or navigate to project directory
cd enterprise-ai-agents

# Make setup script executable
chmod +x setup.sh

# Run automated setup
./setup.sh

# Activate backend environment
cd backend
source venv/bin/activate

# Start backend service
python src/main.py
```

## Project Structure

```
enterprise-ai-agents/
├── extension/              # VS Code Extension (TypeScript)
│   ├── src/
│   ├── package.json
│   └── node_modules/
│
├── backend/                # Python Backend Service
│   ├── venv/              # ⚠️ Virtual Environment (isolated)
│   ├── src/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frameworks/             # Integrated Agent Frameworks
│   ├── crewai/
│   ├── superagi/
│   └── autogpt/
│
├── data/                   # Local data storage
│   ├── chroma/            # Vector DB
│   ├── cache/
│   └── sessions/
│
├── setup.ps1              # Windows setup script
├── setup.sh               # Linux/Mac setup script
└── docker-compose.yml
```

## Virtual Environment Strategy

### Why Virtual Environments?

- **Isolation**: Prevents conflicts with system Python packages
- **Reproducibility**: Ensures consistent dependencies across environments
- **Framework Separation**: Each agent framework can have its own dependencies
- **Clean Development**: Easy to reset and rebuild environments

### Backend Virtual Environment

Located in `backend/venv/`, this contains all Python dependencies for the main backend service:

- FastAPI for REST API and WebSocket
- Sentence Transformers for code embeddings
- ChromaDB for vector storage
- LangChain for LLM orchestration
- Agent framework adapters

### Framework Virtual Environments

Each framework (CrewAI, SuperAGI, AutoGPT) can optionally have its own virtual environment in `frameworks/*/venv/` to prevent dependency conflicts.

## Manual Setup (Alternative)

If you prefer manual setup or the automated script fails:

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2. Extension Setup

```bash
cd extension

# Install Node dependencies
npm install

# Build extension
npm run compile
```

### 3. Data Directories

```bash
# Create data directories
mkdir -p data/chroma
mkdir -p data/cache
mkdir -p data/sessions
```

## Development Workflow

### Starting the Backend

```bash
# Activate virtual environment
cd backend
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Start FastAPI server
python src/main.py

# Or with auto-reload
uvicorn src.main:app --reload
```

### Developing the Extension

1. Open `extension/` folder in VS Code
2. Press `F5` to start debugging
3. A new VS Code window will open with the extension loaded
4. Make changes and reload the extension window

### Running Tests

```bash
# Backend tests
cd backend
.\venv\Scripts\Activate.ps1
pytest tests/ -v

# Extension tests
cd extension
npm test
```

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Backend Configuration
HOST=0.0.0.0
PORT=8000
ENV=development

# LLM Configuration
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=codellama:7b

# Vector DB
CHROMA_PERSIST_DIR=../data/chroma

# Privacy Settings
ALLOW_CLOUD=false
ALLOW_TELEMETRY=false

# Optional Cloud API Keys (only if cloud mode enabled)
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
```

## Troubleshooting

### Virtual Environment Not Activating

**Windows:**
```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Linux/Mac:**
```bash
# Ensure script is executable
chmod +x setup.sh
```

### Python Version Issues

```bash
# Check Python version
python --version  # Should be 3.11+

# Use specific Python version
python3.11 -m venv venv
```

### Dependency Conflicts

```bash
# Clear and reinstall
cd backend
rm -rf venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Port Already in Use

```bash
# Change port in .env file
PORT=8001

# Or kill process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

## Next Steps

1. ✅ Complete setup using automated script
2. 📖 Read the [Design Document](.kiro/specs/enterprise-ai-agents-integration/design.md)
3. 📋 Review [Requirements](.kiro/specs/enterprise-ai-agents-integration/requirements.md)
4. 🔨 Start implementing [Tasks](.kiro/specs/enterprise-ai-agents-integration/tasks.md)
5. 🚀 Begin with Task 1: Project structure and infrastructure

## Key Features

- 🔒 **Privacy-First**: Local-only operation by default
- 🤖 **Multi-Agent**: 6 specialized AI agents working together
- 💠 **Mode Toggle**: Easy switch between offline (local) and online (cloud)
- 🎨 **VS Code Native**: Deep IDE integration
- ⚡ **Real-time**: Inline suggestions as you type
- 🧪 **Test Generation**: Automated test creation
- 🔐 **Security Analysis**: Real-time vulnerability detection

## Support

For issues or questions:
- Check the [Design Document](.kiro/specs/enterprise-ai-agents-integration/design.md)
- Review [Tasks](.kiro/specs/enterprise-ai-agents-integration/tasks.md)
- Open an issue in the project repository

---

**Project Creator:** Herman Swanepoel  
**License:** [Your License]  
**Repository:** [Your Repository URL]
