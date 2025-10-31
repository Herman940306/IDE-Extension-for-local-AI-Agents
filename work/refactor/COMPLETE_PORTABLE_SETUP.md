# 🚀 Complete Portable Setup - Final Structure

## ✅ What Changed

**Folder Structure Simplified:**
```
AI-Agents-Integration/
│
├─ backend/                   ← FastAPI backend code
│   ├─ src/
│   └─ tests/
│
├─ ollama/                    ← Ollama executable (portable)
│   └─ ollama.exe
│
├─ models/                    ← AI models (self-contained!)
│   ├─ manifests/
│   └─ blobs/
│
├─ .venv/                     ← Python virtual environment
│
├─ run_ollama.ps1             ← Start Ollama server
├─ pull_models.ps1            ← Download models locally
├─ start_backend.ps1          ← Start Ollama + Backend together
├─ setup_portable_ollama.ps1  ← One-time setup
└─ RUN_TESTS.ps1              ← Run E2E tests
```

---

## 🎯 Quick Start (3 Commands)

```powershell
# 1. Setup (first time only)
.\setup_portable_ollama.ps1

# 2. Pull models (first time only)
.\pull_models.ps1

# 3. Start everything
.\start_backend.ps1
```

That's it! Backend + Ollama will start automatically.

---

## 📋 Updated Scripts

### 1️⃣ `run_ollama.ps1`
**What it does:**
- Starts Ollama from `.\ollama\ollama.exe`
- Uses local model cache: `.\models\`
- Sets `$env:OLLAMA_MODELS` automatically
- Runs silently in background
- Verifies server is up

**Usage:**
```powershell
.\run_ollama.ps1
```

---

### 2️⃣ `pull_models.ps1`
**What it does:**
- Downloads AI models to `.\models\`
- All models stay in project folder
- Required models:
  - `qwen3:8b` - Fast Reasoner (4.87 GB)
  - `codellama:7b` - Code Engine (3.56 GB)
  - `gemma3:4b` - Fast Model (3.11 GB)
  - `phi3:mini` - Lightweight (2.03 GB)
  - `nomic-embed-text` - Embeddings (0.26 GB)

**Usage:**
```powershell
.\pull_models.ps1
```

---

### 3️⃣ `start_backend.ps1`
**What it does:**
- Starts Ollama automatically
- Waits for Ollama to be ready
- Starts FastAPI backend on port 8001
- Shows logs in real-time

**Usage:**
```powershell
.\start_backend.ps1
```

---

## 🎁 Fully Portable Benefits

### ✅ Self-Contained
- **Ollama:** `.\ollama\ollama.exe`
- **Models:** `.\models\` (12-14 GB)
- **Python:** `.\.venv\`
- **Backend:** `.\backend\`

### ✅ No System Dependencies
- No C:\Users\... paths
- No system-wide Ollama install
- No global Python packages

### ✅ Plug-and-Play
1. Copy folder to USB drive
2. Copy to another Windows PC
3. Run `.\start_backend.ps1`
4. **It just works!** 🎉

---

## 💾 Storage Recommendations

Based on your disk health:

### ⚠️ **E: (NVMe 970 - 500GB)** - Predictive Failure!
**Status:** Failing
**Action:** **Backup NOW** and migrate

### ✅ **F: (Samsung 750 EVO - 250GB SSD)** - Healthy ✨
**Status:** Healthy
**Recommended For:**
- Project code (`.\backend\`, scripts)
- Ollama executable (`.\ollama\`)
- **Best for:** Fast access, low latency

### ✅ **D: (WDC 2TB HDD)** - Healthy
**Status:** Healthy
**Recommended For:**
- AI models (`.\models\`) - 12-14 GB
- Backups
- Logs and datasets
- **Best for:** Large storage, reliable

### ✅ **G: (ST500 HDD)** - Healthy
**Status:** Healthy
**Recommended For:**
- Additional backups
- Archive storage

---

## 🚀 Optimal Setup (SSD + HDD)

**Option A: All on F: (Fastest, but limited space)**
```powershell
# Move entire project to F:
robocopy "E:\..." "F:\AI-Agents-Integration" /E /MT:8
```

**Option B: Split Storage (Recommended)**
```powershell
# Project on F: (SSD for speed)
# Models on D: (HDD for space)

# Set models to D:
$env:OLLAMA_MODELS = "D:\AI_Models"

# Run setup
.\setup_portable_ollama.ps1
.\pull_models.ps1
```

---

## 📊 Disk Space Requirements

| Component | Size | Location |
|-----------|------|----------|
| **Ollama Executable** | ~100 MB | `.\ollama\` |
| **AI Models** | 12-14 GB | `.\models\` |
| **Python + Deps** | ~500 MB | `.\.venv\` |
| **Source Code** | ~50 MB | `.\backend\` |
| **Total** | **~13-15 GB** | |

---

## 🔧 Environment Variable

**Critical for Portability:**
```powershell
$env:OLLAMA_MODELS = "$ProjectRoot\models"
```

This is set automatically by all scripts, ensuring:
- Models load from project folder
- No C:\Users\... paths
- Fully portable between systems

---

## 🧪 Testing

**Run E2E tests:**
```powershell
# Start backend first (in Terminal 1)
.\start_backend.ps1

# Run tests (in Terminal 2)
.\RUN_TESTS.ps1
```

---

## 📦 Shipping Your Project

### Full Package (With Models)
1. Zip entire folder (~15 GB)
2. Copy to new system
3. Extract
4. Run `.\start_backend.ps1`

### Minimal Package (Without Models)
1. Delete `.\models\` folder
2. Zip folder (~600 MB)
3. Copy to new system
4. Extract
5. Run `.\pull_models.ps1` (downloads models)
6. Run `.\start_backend.ps1`

---

## ⚡ Performance Tips

### Use SSD for Active Project
```powershell
# F: drive is your Samsung 750 EVO (healthy SSD)
Move-Item "E:\..." "F:\AI-Agents-Integration"
```

### Use HDD for Model Storage
```powershell
# D: drive is your 2TB WDC (healthy HDD)
$env:OLLAMA_MODELS = "D:\AI_Models"
```

### Symlink for Best of Both
```powershell
# Project on F: (SSD), Models on D: (HDD)
New-Item -ItemType SymbolicLink -Path "F:\AI-Agents-Integration\models" -Target "D:\AI_Models"
```

---

## 🆘 Emergency Backup

**Your NVMe is failing! Backup immediately:**
```powershell
.\BACKUP_TO_D_DRIVE.ps1
```

This will copy everything to **F:\VScode Projects** (healthy SSD).

---

## ✅ Final Checklist

- [ ] Run `.\setup_portable_ollama.ps1` (one-time)
- [ ] Run `.\pull_models.ps1` (downloads ~13 GB)
- [ ] Run `.\start_backend.ps1` (starts everything)
- [ ] Verify: `http://localhost:8001/health`
- [ ] Verify: `http://localhost:11434/api/tags`
- [ ] Run `.\RUN_TESTS.ps1` (E2E tests)
- [ ] **Backup to F:** Run `.\BACKUP_TO_D_DRIVE.ps1`

---

**Project Creator:** Herman Swanepoel
**Date:** October 25, 2025
**Status:** ✅ Fully Portable & Plug-and-Play!
