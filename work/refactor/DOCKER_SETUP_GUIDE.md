# 🚀 Docker Compose Setup - PERMANENT FIX

## ✅ What This Fixes

- **No more "Not connected to backend"** errors
- **Ollama always available** via Docker
- **Redis caching** for performance
- **Production-ready** deployment
- **Health checks** for all services

## 🎯 Quick Start

### Option 1: PowerShell Script (Recommended)
```powershell
.\start-docker.ps1
```

### Option 2: Manual Docker Compose
```powershell
docker-compose up -d
```

### Option 3: Build Fresh Images
```powershell
.\start-docker.ps1 -Build -Logs
```

## 📋 Prerequisites

1. **Docker Desktop** - Must be running
2. **WSL2** - Enabled (for Windows)
3. **Git** - For cloning repository

## 🏗️ Architecture

```
┌─────────────────┐
│  VS Code        │
│  Extension      │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│  Backend API    │◄──── Redis Cache
│  (FastAPI)      │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Ollama Service │◄──── AI Models
│  (Docker)       │      (10+ models)
└─────────────────┘
```

## 🔧 Configuration

All services are configured in `docker-compose.yml`:

- **Backend API**: `http://localhost:8001`
- **Ollama**: `http://localhost:11434`
- **Redis**: `localhost:6379`
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3000`

## 📊 Health Checks

Check all services:
```powershell
curl http://localhost:8001/health | ConvertFrom-Json
```

Expected output:
```json
{
  "status": "healthy",
  "service": "backend",
  "components": {
    "redis": "healthy",
    "cache": {"enabled": true, "size": 0},
    "ollama": {
      "available": true,
      "version": "0.3.12",
      "models_count": 10,
      "models": ["phi3:mini", "qwen3:8b", "codellama:13b", ...]
    }
  }
}
```

## 🎮 Testing the Extension

1. **Start Docker services**:
   ```powershell
   .\start-docker.ps1 -Logs
   ```

2. **Wait for healthy status** (30-60 seconds):
   - Watch logs for "✅ Ollama running version"
   - Backend shows "backend_starting"

3. **Press F5** in VS Code to launch Extension Development Host

4. **Open test file** in new window:
   - File: `test_extension_demo.py`
   - Select lines 14-19 (calculate_total function)

5. **Run command**:
   - Press `Ctrl+Shift+P`
   - Run: "Aura AI: Refactor Code"

6. **Expected UI**:
   ```
   🔧 Analyzing 6 lines for refactoring...
   [Progress bar animation]
   ✨ Code refactored successfully!
   ```

## 🛠️ Troubleshooting

### "Docker is not running"
```powershell
# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### "Service unhealthy"
```powershell
# Check logs for specific service
docker-compose logs ollama
docker-compose logs backend
docker-compose logs redis
```

### "Extension not connecting"
1. Check backend health: `curl http://localhost:8001/health`
2. Reload extension: Press `F5` again
3. Check Extension Output: View → Output → "Aura AI Response"

### "Ollama models missing"
```powershell
# Pull models into Docker container
docker-compose exec ollama ollama pull codellama:7b
docker-compose exec ollama ollama pull qwen3:8b
docker-compose exec ollama ollama pull phi3:mini
```

## 📦 Available Models

After first startup, pull your preferred models:

```bash
# Code generation
ollama pull codellama:13b
ollama pull deepseek-coder:6.7b

# General purpose
ollama pull qwen3:8b
ollama pull phi3:mini

# Embeddings (required)
ollama pull nomic-embed-text:latest
```

## 🔄 Daily Workflow

### Morning startup:
```powershell
.\start-docker.ps1
```

### Development:
- Press `F5` to launch extension
- Make code changes
- Extension auto-reloads

### Evening shutdown:
```powershell
.\start-docker.ps1 -Down
```

## 🎯 Production Deployment

For production use:

1. **Set environment variables**:
   ```bash
   export OLLAMA_HOST=http://ollama:11434
   export REDIS_HOST=redis
   export LOG_LEVEL=INFO
   ```

2. **Use production compose**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Enable SSL** (recommended):
   - Add nginx reverse proxy
   - Use Let's Encrypt certificates

## 📈 Monitoring

Access monitoring dashboards:

- **Prometheus**: http://localhost:9090
  - Metrics: API response times, error rates
  - Queries: Custom PromQL

- **Grafana**: http://localhost:3000
  - Default login: admin/admin
  - Pre-configured AuraIA dashboard

## 🚨 Emergency Commands

### Stop everything:
```powershell
docker-compose down
```

### Reset everything (CAUTION - deletes data):
```powershell
docker-compose down -v
docker system prune -a
```

### View resource usage:
```powershell
docker stats
```

## ✅ Success Checklist

- [ ] Docker Desktop running
- [ ] `docker-compose up -d` successful
- [ ] Backend health check passes
- [ ] Ollama models pulled
- [ ] Extension launches with F5
- [ ] Status bar shows "$(check) Aura AI: Connected"
- [ ] Test command works on sample code

## 🎉 You're Done!

The extension will now:
- ✅ Auto-connect to backend
- ✅ Use Ollama for AI inference
- ✅ Cache responses in Redis
- ✅ Show polished UI with emojis
- ✅ Never show "Not connected" again (if services are running)

## 📚 Additional Resources

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Ollama Models Library](https://ollama.ai/library)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [VS Code Extension API](https://code.visualstudio.com/api)

---

**Created by**: Herman Swanepoel
**Date**: October 25, 2025
**Status**: ✅ PRODUCTION READY
