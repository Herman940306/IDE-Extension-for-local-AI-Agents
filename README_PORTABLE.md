# 🚀 Portable Setup Instructions

## Quick Start (3 Commands)

```powershell
# 1. Setup portable Ollama (one-time)
.\setup_portable_ollama.ps1

# 2. Start Ollama server
.\start_ollama.ps1

# 3. Run tests
.\RUN_TESTS.ps1
```

---

## What is Portable Mode?

This project is **100% self-contained**:
- ✅ Ollama runs from `.\ollama\ollama.exe` (no system install needed)
- ✅ Models stored in `.\ollama_models\` (no `C:\Users\...` paths)
- ✅ Python virtual environment in `.\.venv\`
- ✅ **Copy entire folder → Works on any Windows PC**

---

## Full Setup

### 1️⃣ Setup Portable Ollama (First Time Only)

```powershell
.\setup_portable_ollama.ps1
```

**This will:**
- Create `.\ollama\` folder
- Copy `ollama.exe` from system install (or download it)
- Create `.\ollama_models\` for local model storage
- Optionally copy existing models (~30 GB)
- Generate helper scripts

### 2️⃣ Pull Required Models

```powershell
.\pull_models.ps1
```

**Downloads these models:**
- `qwen3:8b` - System 1 Fast Reasoner (4.87 GB)
- `codellama:7b` - Code Engine (3.56 GB)  
- `gemma3:4b` - Fast Model (3.11 GB)
- `nomic-embed-text` - Embeddings (0.26 GB)

**Total:** ~12 GB

### 3️⃣ Start Ollama Server

```powershell
.\start_ollama.ps1
```

**Server runs at:** `http://localhost:11434`

### 4️⃣ Run Tests

```powershell
# Full test suite
.\RUN_TESTS.ps1

# Single test (faster)
.\RUN_TESTS.ps1 -SingleTest -TestName "test_code_generation_task"

# Skip diagnostic test
.\RUN_TESTS.ps1 -SkipDiagnostic
```

---

## Project Structure (Portable)

```
AI-Agents-Integration/
│
├─ ollama/
│  └─ ollama.exe                    ← Portable Ollama executable
│
├─ ollama_models/                   ← Local model storage
│  ├─ manifests/
│  ├─ blobs/
│  └─ ...
│
├─ backend/                         ← FastAPI backend
│  ├─ src/
│  ├─ tests/
│  └─ diagnostic_test.py
│
├─ .venv/                           ← Python virtual environment
│
├─ setup_portable_ollama.ps1        ← One-time setup
├─ start_ollama.ps1                 ← Start Ollama server
├─ pull_models.ps1                  ← Download models
├─ RUN_TESTS.ps1                    ← Run E2E tests
└─ README_PORTABLE.md               ← This file
```

---

## Shipping to Another System

### Option A: With Models (Recommended)

1. **Zip entire folder** (~30-40 GB with models)
2. **Copy to new system**
3. **Extract and run:**
   ```powershell
   .\start_ollama.ps1
   .\RUN_TESTS.ps1
   ```

### Option B: Without Models (Smaller)

1. **Delete `ollama_models\` folder**
2. **Zip entire folder** (~500 MB without models)
3. **Copy to new system**
4. **Extract and run:**
   ```powershell
   .\start_ollama.ps1
   .\pull_models.ps1      # Download models
   .\RUN_TESTS.ps1
   ```

---

## Troubleshooting

### ❌ "Ollama not found"
**Fix:** Run `.\setup_portable_ollama.ps1` first

### ❌ "No models available"
**Fix:** Run `.\pull_models.ps1`

### ❌ "Port 11434 already in use"
**Fix:** 
```powershell
Get-Process ollama* | Stop-Process -Force
.\start_ollama.ps1
```

### ❌ "Backend failed to start"
**Fix:**
```powershell
# Check Python venv
Test-Path .\.venv\Scripts\python.exe

# Reinstall dependencies
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

---

## Environment Variables

The portable setup automatically sets:

```powershell
$env:OLLAMA_MODELS = "E:\Your\Project\ollama_models"
```

**This ensures:**
- Models stay in project folder
- No conflicts with system Ollama
- Fully portable between systems

---

## Performance Tips

### 🚀 Speed Up Model Loading

Use smaller models for testing:

```powershell
# Edit backend\src\core\config.py
default_model: str = "gemma3:4b"   # Instead of qwen3:8b
```

### 💾 Reduce Disk I/O

Move `ollama_models\` to SSD:

```powershell
# Create symlink (requires admin)
New-Item -ItemType SymbolicLink -Path ".\ollama_models" -Target "D:\Fast_SSD\ollama_models"
```

### 🔧 Optimize for Low RAM

```powershell
# Keep only 1-2 models loaded
# Edit backend\src\config\settings.py
reasoner_keep_alive: str = "5m"    # Instead of 30m
verifier_keep_alive: str = "5m"    # Instead of 10m
```

---

## System Requirements

**Minimum:**
- Windows 10/11
- 8 GB RAM
- 20 GB disk space
- NVIDIA GPU (recommended but not required)

**Recommended:**
- 16 GB+ RAM
- 50 GB+ disk space (for multiple models)
- NVIDIA GPU with 6+ GB VRAM

---

## Credits

**Project Creator:** Herman Swanepoel  
**License:** MIT  
**GitHub:** [Your Repo Here]

---

## Next Steps

After setup, see:
- `README_AUTOMATION.md` - Complete automation guide
- `DEVELOPER_GUIDE.md` - Development documentation
- `API_REFERENCE.md` - API endpoints

🎉 **You're ready to go! Run `.\RUN_TESTS.ps1` to start testing!**
