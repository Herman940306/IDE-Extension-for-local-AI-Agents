# 🚀 Deployment Guide - Enterprise AI Agents Backend

**Project Creator:** Herman Swanepoel
**Target:** VS Code Insider on Windows PC

---

## Prerequisites

- ✅ Python 3.13+
- ✅ Redis (optional, for caching)
- ✅ Git
- ✅ VS Code Insider

---

## Step 1: Merge Feature Branch

```bash
# Switch to main branch
git checkout main

# Merge refactoring changes
git merge feature/system-refactoring-v1

# Push to remote
git push origin main
```

---

## Step 2: Install Dependencies

```bash
# Navigate to backend
cd backend

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3: Configure Environment

Create `.env` file in project root:

```env
# Database
DB_REDIS_URL=redis://localhost:6379
DB_REDIS_MAX_CONNECTIONS=50
DB_REDIS_MIN_IDLE=10

# LLM
LLM_OLLAMA_URL=http://localhost:11434
LLM_DEFAULT_MODEL=codellama:7b
LLM_TIMEOUT=30

# Cache
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# App
DEBUG=false
LOG_LEVEL=INFO
```

---

## Step 4: Start Redis (Optional)

**Option A: Docker**

```bash
docker run -d -p 6379:6379 redis:latest
```

**Option B: Windows Service**

- Download Redis for Windows
- Install and start service

**Option C: Skip Redis**

- Backend will run without caching/rate limiting

---

## Step 5: Run Backend

```bash
# From backend directory
cd backend

# Start server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Step 6: Verify Deployment

**Health Check:**

```bash
curl http://localhost:8000/health
```

**Expected Response:**

```json
{
  "status": "healthy",
  "service": "backend",
  "connections": 0,
  "components": {
    "redis": "healthy",
    "cache": {
      "enabled": true,
      "hits": 0,
      "misses": 0
    }
  }
}
```

---

## Step 7: Test API

**Root Endpoint:**

```bash
curl http://localhost:8000/
```

**API Docs:**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Step 8: VS Code Insider Integration

1. **Open Project in VS Code Insider**

   ```bash
   code-insiders .
   ```

2. **Install Extensions:**
   - Python
   - Pylance
   - REST Client

3. **Configure Launch (`.vscode/launch.json`):**

   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "FastAPI Backend",
         "type": "python",
         "request": "launch",
         "module": "uvicorn",
         "args": [
           "src.main:app",
           "--host",
           "0.0.0.0",
           "--port",
           "8000",
           "--reload"
         ],
         "cwd": "${workspaceFolder}/backend",
         "env": {
           "PYTHONPATH": "${workspaceFolder}/backend"
         }
       }
     ]
   }
   ```

4. **Press F5 to Debug**

---

## Troubleshooting

### Redis Connection Failed

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# If not installed, backend runs without Redis
# Check logs: "redis_unavailable"
```

### Import Errors

```bash
# Ensure virtual environment is activated
.venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

```bash
# Change port in command
python -m uvicorn src.main:app --port 8001 --reload
```

### Module Not Found

```bash
# Set PYTHONPATH
set PYTHONPATH=%CD%\backend
```

---

## Production Deployment (Docker)

```bash
# Build image
docker-compose build backend

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

---

## Quick Start Commands

```bash
# Full deployment
cd backend
.venv\Scripts\activate
python -m uvicorn src.main:app --reload

# With Redis
docker run -d -p 6379:6379 redis:latest
python -m uvicorn src.main:app --reload

# Production
docker-compose up -d
```

---

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Health endpoint returns 200
- [ ] Redis connected (or gracefully disabled)
- [ ] API docs accessible
- [ ] Structured logs visible
- [ ] VS Code debugger works

---

## Support

**Issues?** Check logs:

```bash
# Backend logs show structured JSON
# Look for: "backend_starting", "redis_connected", "services_initialized"
```

**Project Creator:** Herman Swanepoel
**Version:** 1.0.0
**Status:** ✅ PRODUCTION READY
