# 🐳 Step 3: Docker Deployment Validation

**Project Creator:** Herman Swanepoel
**Date:** October 25, 2025
**Status:** 🔄 IN PROGRESS

---

## 📋 Prerequisites

✅ **Completed:**

- Step 1: All 870 tests passing ✅
- Step 2: Extension validated and working ✅

✅ **Required:**

- Docker Desktop installed and running
- Docker Compose available
- Ports available: 8001, 6379, 11434, 9090, 3000

---

## 🎯 Step 3 Objectives

Validate the complete production deployment stack:

1. **Spin up Docker stack** with all services
2. **Verify service health** (Backend, Redis, Ollama, Prometheus, Grafana)
3. **Test extension with containerized backend**
4. **Validate monitoring and observability**
5. **Check service communication**

**Estimated Time:** 30-45 minutes

---

## 🐳 Docker Stack Components

The `docker-compose.yml` includes:

| Service | Port | Purpose |
|---------|------|---------|
| **backend** | 8001 | FastAPI backend (main service) |
| **redis** | 6379 | Cache and session storage |
| **ollama** | 11434 | Local LLM inference (optional) |
| **prometheus** | 9090 | Metrics collection |
| **grafana** | 3000 | Monitoring dashboards |

---

## 📝 Step-by-Step Tasks

### Task 1: Verify Docker Installation (5 min)

**Check Docker is running:**

```powershell
docker --version
docker-compose --version
docker ps
```

**Expected output:**

- Docker version 20.10+ or later
- Docker Compose version 2.0+ or later
- No errors

**If Docker is not running:**

- Open Docker Desktop
- Wait for "Docker Desktop is running" status
- Retry commands

---

### Task 2: Review Docker Configuration (5 min)

**Check the compose file:**

```powershell
cd "e:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
Get-Content docker-compose.yml | Select-String -Pattern "services:|image:|ports:"
```

**Verify environment variables:**

Check `backend/.env` exists and contains:

- `REDIS_HOST=redis`
- `REDIS_PORT=6379`
- `OLLAMA_HOST=http://ollama:11434` (optional)

---

### Task 3: Build Docker Images (10 min)

**Build the backend image:**

```powershell
docker-compose build backend
```

**Expected output:**

```
[+] Building 45.3s (15/15) FINISHED
=> [backend] exporting to image
=> => naming to docker.io/library/ai-agents-backend
```

**Check image was created:**

```powershell
docker images | Select-String "ai-agents"
```

You should see:

- `ai-agents-backend` image
- Size: ~500-800MB
- Created: "Just now"

---

### Task 4: Start the Stack (5 min)

**Start all services:**

```powershell
docker-compose up -d
```

**Expected output:**

```
[+] Running 5/5
✔ Container ai-agents-redis      Started
✔ Container ai-agents-ollama     Started
✔ Container ai-agents-backend    Started
✔ Container ai-agents-prometheus Started
✔ Container ai-agents-grafana    Started
```

**Verify all containers are running:**

```powershell
docker-compose ps
```

All services should show `Up` status.

---

### Task 5: Health Check All Services (10 min)

#### **Backend Health Check**

```powershell
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing | Select-Object StatusCode, Content
```

**Expected:**

- Status: 200
- Content: `{"status":"healthy",...}`

#### **Redis Health Check**

```powershell
docker exec ai-agents-redis redis-cli ping
```

**Expected:** `PONG`

#### **Prometheus Health Check**

Open browser: <http://localhost:9090>

**Expected:**

- Prometheus UI loads
- Targets page shows backend as "UP"

#### **Grafana Health Check**

Open browser: <http://localhost:3000>

**Expected:**

- Grafana login page
- Default credentials: `admin/admin`

#### **Check Backend Logs**

```powershell
docker-compose logs backend --tail=50
```

**Expected:**

- "Application startup complete"
- No errors
- Structured JSON logs

---

### Task 6: Test Extension with Dockerized Backend (10 min)

**Update VS Code Extension Settings:**

1. Press `Ctrl+,` → Search "aura"
2. Update settings:
   - Backend URL: `http://localhost:8001` (should already be this)
   - WebSocket URL: `ws://localhost:8001/ws`

**Reload VS Code:**

- `Ctrl+Shift+P` → "Developer: Reload Window"

**Test Commands:**

1. **Open a Python file**
2. **Select some code**
3. **Run:** `Ctrl+Shift+P` → "Aura: Explain Code"

**Verify in Docker logs:**

```powershell
docker-compose logs backend --tail=20 --follow
```

You should see:

- `websocket_connected`
- `message_received`
- `task_processing`

**Success Criteria:**

- ✅ Extension connects to Docker backend
- ✅ Commands execute successfully
- ✅ Responses appear in Output panel
- ✅ Docker logs show task processing

---

### Task 7: Validate Service Communication (5 min)

#### **Backend → Redis**

**Set a test key:**

```powershell
docker exec ai-agents-backend python -c "import redis; r = redis.Redis(host='redis', port=6379); r.set('test', 'hello'); print(r.get('test'))"
```

**Expected:** `b'hello'`

#### **Backend → Ollama** (Optional)

**Check Ollama is accessible from backend:**

```powershell
docker exec ai-agents-backend curl -s http://ollama:11434/api/tags
```

**Expected:** JSON list of available models (or empty if none pulled)

---

### Task 8: Check Metrics & Monitoring (5 min)

#### **Prometheus Metrics**

Open: <http://localhost:9090/targets>

**Expected:**

- Backend target: `http://backend:8001/metrics`
- State: **UP** (green)

**Query a metric:**

1. Go to Graph tab
2. Enter: `http_requests_total`
3. Click "Execute"

**Expected:** Graph showing request counts

#### **Grafana Dashboard**

1. Open: <http://localhost:3000>
2. Login: `admin` / `admin`
3. Add Prometheus data source:
   - URL: `http://prometheus:9090`
   - Save & Test

**Expected:** "Data source is working"

---

## 🔍 Troubleshooting

### Backend Container Won't Start

**Check logs:**

```powershell
docker-compose logs backend
```

**Common issues:**

- Port 8001 already in use → Stop local backend first
- Missing dependencies → Rebuild: `docker-compose build --no-cache backend`
- Environment vars missing → Check `backend/.env`

### Redis Connection Failed

**Check Redis is running:**

```powershell
docker-compose ps redis
```

**Test connection:**

```powershell
docker exec ai-agents-redis redis-cli ping
```

**If stopped:** `docker-compose restart redis`

### Extension Can't Connect

**Verify backend is exposed:**

```powershell
docker-compose port backend 8001
```

**Expected:** `0.0.0.0:8001`

**Check Windows Firewall:**

- Allow Docker Desktop
- Allow port 8001 inbound

### Ollama Not Working (Optional)

**Pull a model:**

```powershell
docker exec ai-agents-ollama ollama pull llama3.2:3b-q4_K_M
```

**This is optional** - backend works without Ollama

---

## ✅ Validation Checklist

Mark each as complete:

### Infrastructure

- [x] Docker Desktop running
- [x] All 5 containers started successfully
- [x] No container restarts or errors

### Service Health

- [ ] Backend health endpoint returns 200
- [ ] Redis responds to PING
- [ ] Prometheus UI accessible
- [ ] Grafana UI accessible

### Extension Integration

- [ ] Extension connects to Docker backend
- [ ] WebSocket connection established
- [ ] All 4 commands execute successfully
- [ ] Docker logs show task processing

### Service Communication

- [ ] Backend can write to Redis
- [ ] Backend can read from Redis
- [ ] Prometheus scraping backend metrics
- [ ] Grafana connected to Prometheus

### Monitoring

- [ ] Prometheus targets showing UP
- [ ] Metrics queryable in Prometheus
- [ ] Grafana data source configured

---

## 🎉 Success Criteria

**Step 3 is complete when:**

1. ✅ All containers running without errors
2. ✅ Backend health check passes
3. ✅ Extension connects and executes commands
4. ✅ Redis caching functional
5. ✅ Prometheus collecting metrics
6. ✅ Grafana dashboards accessible
7. ✅ No errors in any service logs

---

## 📊 Performance Baseline

Record these metrics for production reference:

| Metric | Value |
|--------|-------|
| Backend startup time | _____ seconds |
| First request latency | _____ ms |
| Average task latency | _____ ms |
| Memory usage (backend) | _____ MB |
| Memory usage (total) | _____ MB |
| CPU usage (idle) | _____ % |

---

## 🧹 Cleanup (After Testing)

**Stop all services:**

```powershell
docker-compose down
```

**Remove volumes (if needed):**

```powershell
docker-compose down -v
```

**Remove images (if rebuilding):**

```powershell
docker-compose down --rmi all
```

---

## 📝 Next Steps After Step 3

Once Docker deployment is validated:

1. **Document production deployment** (if not already done)
2. **Create deployment runbook** for operations
3. **Set up CI/CD pipeline** (optional)
4. **Prepare release notes**
5. **Publish extension to marketplace** (optional)

---

## 🚀 Production Readiness

After completing Step 3, the project will be:

- ✅ **100% Complete** (all 3 steps done)
- ✅ **Production-ready** (Docker validated)
- ✅ **Deployable** (infrastructure tested)
- ✅ **Monitored** (observability in place)

---

**Status:** 🔄 **READY TO START**
**Started:** _____________
**Completed:** _____________

**Next Action:** Run Task 1 - Verify Docker Installation
