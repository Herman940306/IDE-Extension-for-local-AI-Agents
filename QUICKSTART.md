# 🚀 AuraIA Quick Start Guide

## Prerequisites

### 1. Install Ollama
Download and install Ollama from [ollama.ai](https://ollama.ai)

**Windows:**
```powershell
# Download OllamaSetup.exe and run it
# Or use winget:
winget install Ollama.Ollama
```

### 2. Download Required Models
```powershell
# Start Ollama service
ollama serve

# In a new terminal, download models:
ollama pull llama3.2:3b          # Fast reasoner (~2GB)
ollama pull codellama:7b          # Code generation (~4GB)
ollama pull nomic-embed-text      # Embeddings (~274MB)
```

### 3. Install Dependencies

**Backend:**
```powershell
cd backend
pip install -r requirements.txt
```

**Frontend:**
```powershell
cd frontend
npm install
```

**Extension:**
```powershell
cd extension
npm install
```

---

## 🎯 Running AuraIA

### Start Backend (Terminal 1)
```powershell
cd backend
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8001
```

### Start Frontend (Terminal 2)
```powershell
cd frontend
npm run dev
```

### Start Extension Development (Terminal 3)
```powershell
cd extension
# Press F5 in VS Code to launch Extension Development Host
```

---

## 🧪 Testing

Visit `http://localhost:3000` to test the frontend interface.

**Test the AI:**
1. Type: "1+1"
2. Type: "write a hello world function in python"
3. Type: "explain what this code does: `def factorial(n): return 1 if n <= 1 else n * factorial(n-1)`"

---

## ⚙️ Configuration

### Environment Variables
Create `backend/.env`:
```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Models
REASONER_MODEL=llama3.2:3b
VERIFIER_MODEL=mistral:7b
ADVANCED_MODEL=codellama:13b-instruct-q4_0
```

---

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
pip install -r backend/requirements.txt --force-reinstall
```

### Ollama connection failed
```powershell
# Check if Ollama is running
curl http://localhost:11434/api/version

# Restart Ollama service
# Windows: Restart from system tray
```

### Models not found
```powershell
# List installed models
ollama list

# Re-download if missing
ollama pull llama3.2:3b
```

### Frontend connection issues
- Check backend is running on port 8001
- Check frontend is running on port 3000
- Check WebSocket connection in browser console

---

## 📚 Next Steps

1. **Read the Architecture:** Check `ARCHITECTURE_V2_NEXTGEN.md`
2. **Explore Agents:** See `backend/src/agents/`
3. **Customize Models:** Edit `backend/src/config/settings.py`
4. **Add Custom Agents:** Follow `DEVELOPER_GUIDE.md`

---

## 🔗 Useful Links

- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/README.md)
- [VS Code Extension API](https://code.visualstudio.com/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 💬 Need Help?

- 🐛 Report issues on GitHub
- 💬 Join our Discord community
- 📖 Read the full documentation

---

**Welcome to AuraIA - The Future Beside You! 🚀**
