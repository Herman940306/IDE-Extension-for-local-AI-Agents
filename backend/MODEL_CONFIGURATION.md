# AuraIA Model Configuration Guide

**Optimized for: NVIDIA 1080 Ti (11GB VRAM) + 16GB RAM**

---

## 🎯 **Recommended Model Setup**

| Role | Primary Model | Precision | Device | VRAM | Fallbacks |
|------|---------------|-----------|--------|------|-----------|
| **System 1 Fast Reasoner** | `qwen3:8b-q4_K_M` | Q4 | GPU | ~4.5GB | `llama3.2:3b`, `phi3:mini` |
| **Code Engine** | `codellama:7b-q4_K_M` | Q4 | GPU | ~4.0GB | `mistral:7b`, `llama3.2:3b` |
| **System 2 Verifier** | `deepseek-r1:8b-q4_K_M` | Q4 | CPU Fallback | ~4.5GB | `mistral:7b`, `llama3.2:3b` |
| **Context Engine** | `nomic-embed-text` | FP16 | CPU | ~500MB | *(none)* |
| **Safety Layer** | `phi3:mini` | FP16 | CPU | ~2.0GB | `llama3.2:3b` |
| **UX/Tone** | `gemma3:4b` | FP16 | GPU | ~2.5GB | `phi3:mini`, `llama3.2:3b` |

**Total Resource Usage:**
- **VRAM**: ~10GB (under 11GB limit)
- **System RAM**: ~12-13GB (under 16GB limit)
- **Models loaded concurrently**: 3-4 (optimal for responsiveness)

---

## 🔧 **Installation Commands**

```bash
# Primary Models (GPU, Q4 quantization)
ollama pull qwen3:8b-q4_K_M
ollama pull codellama:7b-q4_K_M
ollama pull deepseek-r1:8b-q4_K_M

# Utility Models (CPU-friendly)
ollama pull nomic-embed-text
ollama pull phi3:mini
ollama pull gemma3:4b

# Fallback Models (if not already installed)
ollama pull mistral:7b
ollama pull llama3.2:3b
```

---

## ⚙️ **Configuration Settings**

Edit `backend/src/config/settings.py` or create `.env` file:

```env
# UI/UX Configuration (TOGGLEABLE)
SHOW_MODEL_NAMES_IN_RESPONSES=false   # Hide model routing from user
SHOW_SYSTEM_FEEDBACK=false            # Hide backend logs from user
CLEAN_USER_EXPERIENCE=true            # Only show AI-user conversation

# Model Configuration
REASONER_MODEL=qwen3:8b-q4_K_M
CODE_ENGINE_MODEL=codellama:7b-q4_K_M
VERIFIER_MODEL=deepseek-r1:8b-q4_K_M
```

### **Toggleable Features:**

| Setting | Default | Description |
|---------|---------|-------------|
| `show_model_names_in_responses` | `false` | Hide "Routed to codellama:7b" messages |
| `show_system_feedback` | `false` | Hide "Processing with System1..." logs |
| `clean_user_experience` | `true` | Show only user ↔ AI conversation |

**To Enable System Feedback** (for debugging):
```python
# In settings.py
show_model_names_in_responses = True
show_system_feedback = True
clean_user_experience = False
```

---

## 🔄 **Automatic Fallback Strategy**

The router automatically tries fallback models if primary model is unavailable:

### Example: Chat Task Routing

```
1. TRY: qwen3:8b-q4_K_M  (primary)
   ↓ (if unavailable)
2. TRY: llama3.2:3b      (fallback 1)
   ↓ (if unavailable)
3. TRY: phi3:mini        (fallback 2)
   ↓ (if unavailable)
4. ERROR: No models available
```

### Fallback Configuration:

Edit `backend/src/orchestrator/multi_model_router.py`:

```python
ModelRole.SYSTEM1_FAST: ModelConfig(
    name="qwen3:8b-q4_K_M",
    fallback_models=["llama3.2:3b", "phi3:mini"],  # <-- Add/remove fallbacks here
    role=ModelRole.SYSTEM1_FAST,
    ...
)
```

---

## 📊 **Model Performance Benchmarks**

| Model | Task Type | Avg Latency | Quality | VRAM |
|-------|-----------|-------------|---------|------|
| `qwen3:8b-q4_K_M` | Chat, General | 150-300ms | ⭐⭐⭐⭐⭐ | 4.5GB |
| `codellama:7b-q4_K_M` | Code Gen | 200-500ms | ⭐⭐⭐⭐⭐ | 4.0GB |
| `deepseek-r1:8b-q4_K_M` | Verification | 1-2s | ⭐⭐⭐⭐ | 4.5GB |
| `phi3:mini` | Quick Help | 100-200ms | ⭐⭐⭐ | 2.0GB |
| `llama3.2:3b` | Emergency | 150-300ms | ⭐⭐⭐ | 2.0GB |

---

## 🎨 **Clean User Experience**

### **Before** (verbose):
```
User: hi
System: Routed GENERAL task to qwen3:8b-q4_K_M
System: Processing with System1 Fast Reasoner...
System: Generated response in 245ms
AI: Hello! How can I help you today?
```

### **After** (clean):
```
User: hi
AI: Hello! How can I help you today?
```

All routing, processing, and model selection happens **behind the scenes**.

---

## 🚀 **Quick Start**

1. **Pull required models:**
   ```bash
   ollama pull qwen3:8b-q4_K_M
   ollama pull codellama:7b-q4_K_M
   ollama pull phi3:mini
   ollama pull llama3.2:3b
   ```

2. **Verify configuration:**
   ```python
   # backend/src/config/settings.py
   show_model_names_in_responses = False  # ✅ Clean UX
   ```

3. **Start backend:**
   ```bash
   cd backend
   python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8001
   ```

4. **Test adaptive personality:**
   ```bash
   python backend/test_adaptive_personality.py
   ```

---

## 📝 **Notes**

- **Q4 Quantization**: Reduces VRAM by ~50% with minimal quality loss
- **Keep Alive**: Models stay in memory for fast responses (configurable per model)
- **CPU Fallback**: `deepseek-r1:8b` can run on CPU if GPU saturated
- **Automatic Retry**: Router retries with fallback models on timeout/error

**Model Naming**: All model references removed from user-facing responses to maintain clean conversation flow.
