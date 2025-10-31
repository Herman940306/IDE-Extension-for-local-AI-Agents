# 🤖 Model Selection Guide for AuraIA

**Project**: AuraIA Enterprise AI Agents Integration System
**Purpose**: Code generation, refactoring, bug fixing, documentation
**Date**: October 14, 2025

---

## 📊 Your Current Models

| Model                           | Size   | Best For                  | Speed       | Quality            |
| ------------------------------- | ------ | ------------------------- | ----------- | ------------------ |
| **llama3.2:3b**                 | 2.0 GB | General tasks, chat       | ⚡⚡⚡ Fast | ⭐⭐⭐ Good        |
| **llama3.1:8b-instruct-q4_K_M** | 4.9 GB | Complex reasoning, coding | ⚡⚡ Medium | ⭐⭐⭐⭐ Excellent |
| **local-ha-supervisor:latest**  | 4.9 GB | Custom/unknown            | ⚡⚡ Medium | ❓ Unknown         |

---

## 🎯 Recommendations for AuraIA (Code-Focused)

### Refactored model roles (GTX 1080 Ti profile)

| Role | Model | GPU / CPU | Memory Usage (VRAM / RAM) | Latency (per 1K tokens) | Tasks / Notes | Loading Strategy |
| --- | --- | --- | --- | --- | --- | --- |
| **System 1 – Fast Reasoner** | `llama3.2:3b` Q4_K_M | GPU | ~3–4 GB VRAM | 0.7–1.2 s | Quick code suggestions, comments, small refactors | Always loaded on GPU |
| **System 2 – Analytical Verifier** | `mistral:7b` Q4_K_M | GPU | ~9 GB VRAM | 2–4 s | Multi-step reasoning, correctness verification, structured output | Load on demand, keep resident while analyzing complex tasks |
| **Optional Advanced Reasoning** | `codellama:13b-instruct` Q4_0 | CPU | ~13–14 GB RAM | 10–15 s | Deep refactors, multi-function analysis; approximates GPT-4.1 reasoning | Load only when really needed; fallback if GPU busy |
| **Conversational / UX Layer** | `gemma2:9b` Q4_K_M | GPU (optional) | ~10–11 GB VRAM | 3–5 s | Chat-style explanations, contextual dialogue | Load on demand; unload after conversation |
| **Embeddings / Search** | `nomic-embed-text` | CPU | ~1 GB | <0.01 s | Code/doc search, context retrieval | Always resident on CPU |
| **Safety / Final Check** | `phi3-medium` | CPU | ~1 GB | ~1 s | Final output sanity check, sensitive info detection | Always loaded on CPU |
| **Summarization / Optional Flow** | `phi3-mini` | CPU | ~1 GB | 1–2 s | Summaries, condensed explanations | Load when needed |

Key configuration notes implemented in code:

- VRAM guardrails: We keep System 1 resident and set short keep-alive for System 2, with the 13B advanced model forced to CPU and unloaded immediately after use.
- Latency and responsiveness: System 1 path remains sub-second; escalation triggers System 2 (2–4s), and only very complex cases escalate to 13B on CPU.
- Dual-Process orchestration: System 1 runs first; low confidence/complexity escalates to System 2; extreme complexity will temporarily switch the verifier to the advanced 13B model; merged output can go through an optional `phi3-medium` safety pass.
- CPU residency: Safety (`phi3-medium`) and summarizer (`phi3-mini`) are configured for CPU with keep-alive tuned; embeddings remain Sentence-Transformers by default with a configuration knob for `nomic-embed-text` via Ollama.

Practical tips:

- Interactive IDE usage: Keep only System 1 and embeddings resident for instant responses.
- Complex PRs / multi-file tasks: Temporarily load Mistral 7B; fallback to Codellama 13B for deep reasoning when needed.
- Long-running sessions: Monitor GPU memory with `nvidia-smi`; optional models are set to unload when idle to protect VRAM.

### 🔀 Execution Approaches (choose based on your hardware/privacy)

| Approach | Models | Notes / Trade-offs |
| --- | --- | --- |
| **Local + quantized “mini-GPT4”** | `llama3.1:8b`, `mistral:7b`, or `codellama:13b` (Q4_0) | Approaches GPT‑4.1-like logic for code with dual‑process orchestration; slower on large files but acceptable when System 1 filters first. |
| **Hybrid local + small cloud verification** | Local `llama3.2:3b` or `mistral:7b` for System 1 + cloud GPT‑4.1 for System 2 | True GPT‑4.1 reasoning, but code leaves your machine; can cache locally; enable only when privacy constraints allow. |
| **Chunking + iterative reasoning** | Keep `mistral:7b` for System 2; chunk complex files, then merge | Simulates GPT‑4.1 stepwise reasoning fully offline; latency grows roughly linearly with file size; good for very large modules. |

### ⭐ BEST CHOICE: Qwen2.5-Coder (Specialized for Coding)

**Why**: Qwen2.5-Coder is specifically trained for code generation and outperforms many larger models.

```powershell
# Recommended: 7B version (best balance)
ollama pull qwen2.5-coder:7b

# Alternative: 3B version (if you need speed)
ollama pull qwen2.5-coder:3b

# Alternative: 14B version (if you have GPU/RAM)
ollama pull qwen2.5-coder:14b
```

**Benchmarks**:

- HumanEval: 65.9% (7B) - Better than GPT-3.5
- MBPP: 70.2%
- Speed: 40-60 tokens/sec on CPU
- Quality: Specialized for Python, JavaScript, TypeScript, etc.

---

## 🏆 Top Model Recommendations by Use Case

### Option 1: Speed Priority (Your Current Setup)

**Use**: llama3.2:3b + llama3.1:8b-instruct

✅ **Already installed!**

```bash
REASONER_MODEL=llama3.2:3b                    # Fast, good for simple tasks
VERIFIER_MODEL=llama3.1:8b-instruct-q4_K_M    # Better for verification
SUMMARIZER_MODEL=llama3.2:3b                  # Fast summaries
```

**Pros**:

- ✅ Already downloaded
- ✅ Very fast responses (40-80 tokens/sec)
- ✅ Low RAM usage (~6-8GB total)
- ✅ Good for real-time coding assistance

**Cons**:

- ⚠️ May struggle with complex algorithms
- ⚠️ Not specialized for code

**Best for**: Real-time suggestions, quick refactoring, simple bug fixes

---

### Option 2: Code Quality Priority (RECOMMENDED)

**Use**: Qwen2.5-Coder series

```powershell
# Pull the models
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:3b
```

Then update `.env`:

```bash
REASONER_MODEL=qwen2.5-coder:7b           # Best for complex code
VERIFIER_MODEL=qwen2.5-coder:7b           # Verify code quality
SUMMARIZER_MODEL=qwen2.5-coder:3b         # Fast documentation
```

**Pros**:

- ✅ **Specialized for coding** (Python, JS, TS, Go, Rust, etc.)
- ✅ Beats GPT-3.5 on coding benchmarks
- ✅ Better at following code patterns
- ✅ Excellent at bug detection

**Cons**:

- ⚠️ Larger download (7B = ~4.7GB)
- ⚠️ Slower than 3B models (~30-50 tokens/sec)

**Best for**: Production code generation, complex refactoring, architecture decisions

---

### Option 3: Balanced Approach (BEST OF BOTH)

**Use**: Mix of fast + quality models

```powershell
# Download Qwen for code-heavy tasks
ollama pull qwen2.5-coder:7b
```

Update `.env`:

```bash
# Use fast model for quick tasks, quality model for complex tasks
REASONER_MODEL=qwen2.5-coder:7b              # Complex code reasoning
VERIFIER_MODEL=qwen2.5-coder:7b              # Code verification
SUMMARIZER_MODEL=llama3.2:3b                 # Fast summaries (already installed)

# Backup/fallback model
LLM_DEFAULT_MODEL=llama3.1:8b-instruct-q4_K_M
```

**Pros**:

- ✅ Best code quality where it matters
- ✅ Fast summaries/documentation
- ✅ Efficient resource usage

**Best for**: Professional development, production systems

---

## 🎓 Model Comparison Chart

### Coding-Specific Models

| Model                   | Size  | HumanEval | Speed  | Code Quality | RAM |
| ----------------------- | ----- | --------- | ------ | ------------ | --- |
| **qwen2.5-coder:7b** ⭐ | 4.7GB | 65.9%     | ⚡⚡   | ⭐⭐⭐⭐⭐   | 8GB |
| **qwen2.5-coder:3b**    | 2.0GB | 52.4%     | ⚡⚡⚡ | ⭐⭐⭐⭐     | 4GB |
| **codellama:7b**        | 3.8GB | 29.9%     | ⚡⚡   | ⭐⭐⭐       | 8GB |
| **deepseek-coder:6.7b** | 3.8GB | 48.8%     | ⚡⚡   | ⭐⭐⭐⭐     | 8GB |

### General Models (Current)

| Model                   | Size  | HumanEval | Speed    | Code Quality | RAM  |
| ----------------------- | ----- | --------- | -------- | ------------ | ---- |
| **llama3.2:3b** (yours) | 2.0GB | ~35%      | ⚡⚡⚡   | ⭐⭐⭐       | 4GB  |
| **llama3.1:8b** (yours) | 4.9GB | ~45%      | ⚡⚡     | ⭐⭐⭐⭐     | 10GB |
| **llama3.2:1b**         | 1.3GB | ~25%      | ⚡⚡⚡⚡ | ⭐⭐         | 2GB  |

---

## 💡 My Recommendation for You

Based on your project needs (code generation, refactoring, bug fixing):

### **UPGRADE TO QWEN2.5-CODER:7B** 🎯

**Why?**

1. **60% better at coding** than llama3.2:3b
2. **Specialized training** on code repositories
3. **Better bug detection** and security awareness
4. **Still fast enough** for real-time use (~40 tokens/sec)

**How?**

```powershell
# Step 1: Download the model
ollama pull qwen2.5-coder:7b

# Step 2: Update your .env file
notepad backend\.env

# Change:
# REASONER_MODEL=llama3.2:3b
# To:
# REASONER_MODEL=qwen2.5-coder:7b

# VERIFIER_MODEL=llama3.1:8b-instruct-q4_K_M
# To:
# VERIFIER_MODEL=qwen2.5-coder:7b
```

**Result**: Significantly better code quality with acceptable speed

---

## 🚀 Quick Comparison Test

Want to see the difference? Test both models:

```powershell
# Test llama3.2:3b (your current)
ollama run llama3.2:3b "Write a Python function to validate email addresses using regex"

# Test qwen2.5-coder:7b (recommended)
ollama run qwen2.5-coder:7b "Write a Python function to validate email addresses using regex"
```

Qwen will typically produce:

- ✅ More robust error handling
- ✅ Better regex patterns
- ✅ Cleaner code structure
- ✅ Security considerations

---

## 📋 Action Items

### If You Want BEST Code Quality:

```powershell
# 1. Download Qwen2.5-Coder
ollama pull qwen2.5-coder:7b

# 2. Update .env
REASONER_MODEL=qwen2.5-coder:7b
VERIFIER_MODEL=qwen2.5-coder:7b
SUMMARIZER_MODEL=llama3.2:3b  # Keep fast model for summaries

# 3. Restart backend
python run.py
```

### If You Want to Keep Current (Speed Focus):

```bash
# Your current setup is FINE for:
# - Real-time autocomplete
# - Quick refactoring suggestions
# - Lightweight assistance

# Just update .env to use llama3.1 for verification:
REASONER_MODEL=llama3.2:3b
VERIFIER_MODEL=llama3.1:8b-instruct-q4_K_M  # Use the better model
SUMMARIZER_MODEL=llama3.2:3b
```

---

## 🎯 Final Recommendation

**For AuraIA (Code-focused AI assistant):**

### Download This:

```powershell
ollama pull qwen2.5-coder:7b
```

### Configure This (.env):

```bash
# Primary model for code generation
REASONER_MODEL=qwen2.5-coder:7b

# Verification and quality checks
VERIFIER_MODEL=qwen2.5-coder:7b

# Fast summaries and documentation
SUMMARIZER_MODEL=llama3.2:3b

# Fallback model
LLM_DEFAULT_MODEL=llama3.1:8b-instruct-q4_K_M
```

### Expected Performance:

- **Code Quality**: ⭐⭐⭐⭐⭐ (85/100)
- **Speed**: ⚡⚡⚡ (40-60 tokens/sec)
- **RAM Usage**: ~8GB during inference
- **Accuracy**: Better than GPT-3.5 for code

---

## 📊 Summary Table

| Configuration                      | Code Quality | Speed    | RAM | Download | Best For     |
| ---------------------------------- | ------------ | -------- | --- | -------- | ------------ |
| **Current** (llama3.2:3b)          | ⭐⭐⭐       | ⚡⚡⚡⚡ | 4GB | ✅ Done  | Speed        |
| **Recommended** (qwen2.5-coder:7b) | ⭐⭐⭐⭐⭐   | ⚡⚡⚡   | 8GB | 4.7GB    | **Quality**  |
| **Hybrid** (qwen:7b + llama:3b)    | ⭐⭐⭐⭐     | ⚡⚡⚡   | 8GB | 4.7GB    | **Balanced** |

---

## ❓ FAQ

**Q: Will qwen2.5-coder work with my current code?**
A: Yes! Drop-in replacement, no code changes needed.

**Q: How long to download qwen2.5-coder:7b?**
A: ~4.7GB, takes 5-15 minutes depending on connection.

**Q: Can I use both models?**
A: Yes! AuraIA can use different models for different tasks.

**Q: Will it be slower?**
A: Slightly (30-40 tokens/sec vs 60-80), but code quality is MUCH better.

**Q: Do I need GPU?**
A: No! Works fine on CPU, just a bit slower.

---

## 🎉 Conclusion

**Your Current Setup (llama3.2:3b)**:

- ✅ Good for: Speed, lightweight tasks
- ⚠️ Not ideal for: Complex code, production use

**Recommended Upgrade (qwen2.5-coder:7b)**:

- ✅ **60% better code quality**
- ✅ **Specialized for your use case**
- ✅ **Still fast enough for real-time**
- ⚠️ **One-time 4.7GB download**

**My Advice**: Upgrade to qwen2.5-coder:7b for professional code quality! 🚀

---

**Created**: October 14, 2025
**Author**: Herman Swanepoel
**Next Steps**: Run `ollama pull qwen2.5-coder:7b` and update `.env`
