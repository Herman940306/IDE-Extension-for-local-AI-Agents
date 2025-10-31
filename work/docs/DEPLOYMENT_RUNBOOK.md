<!-- Placeholder: ANTHROPIC_API_KEY not set. Skipping doc rewrite. -->
# Deployment Runbook - Enterprise AI Agents Backend

**Project Creator:** Herman Swanepoel
**Version:** 1.0.0
**Last Updated:** 2025-10-13

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Monitoring](#monitoring)
8. [Maintenance](#maintenance)

---

## Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **Node.js**: 16.x or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Git**: 2.30 or higher

### Required Services

- **Redis**: 7.x (for caching and rate limiting)
- **Ollama**: Latest (for local LLM inference)

### Environment Variables

```bash
# LLM Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Feature Flags
ENABLE_CACHE=true
ENABLE_RATE_LIMITING=true
ALLOW_CLOUD_FALLBACK=false

# Rate Limiting
RATE_LIMIT_DEFAULT_LIMIT=100
RATE_LIMIT_DEFAULT_WINDOW=60

# Request Limits
MAX_REQUEST_SIZE=10485760  # 10MB
MAX_FILE_SIZE=1048576      # 1MB
```

---

## Local Development

### 1. Clone Repository

```bash
git clone https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents.git
cd IDE-Extension-for-local-AI-Agents
```

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Services

```bash
# Start Redis and ChromaDB
docker-compose up -d

# Verify services
docker ps
```

### 4. Start Backend

```bash
# Development mode with auto-reload
python -m uvicorn src.main:app --reload --port 8000

# Or using the script
python -m src.main
```

### 5. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "backend",
#   "connections": 0,
#   "components": {
#     "redis": "healthy",
#     "cache": {...}
#   }
# }

# Check API docs
open http://localhost:8000/docs
```

---

## Staging Deployment

### 1. Prepare Environment

```bash
# Create staging environment file
cp .env.example .env.staging

# Edit staging configuration
nano .env.staging
```

### 2. Build Docker Image

```bash
# Build backend image
docker build -t enterprise-ai-backend:staging -f backend/Dockerfile backend/

# Verify image
docker images | grep enterprise-ai-backend
```

### 3. Deploy with Docker Compose

```bash
# Use staging compose file
docker-compose -f docker-compose.staging.yml up -d

# Check logs
docker-compose -f docker-compose.staging.yml logs -f backend
```

### 4. Run Health Checks

```bash
# Wait for services to start
sleep 10

# Check health
curl http://staging-server:8000/health

# Check Redis connection
docker-compose -f docker-compose.staging.yml exec redis redis-cli ping
```

### 5. Run Smoke Tests

```bash
# Test root endpoint
curl http://staging-server:8000/

# Test WebSocket connection
# (Use WebSocket client tool)

# Test rate limiting
for i in {1..5}; do curl http://staging-server:8000/health; done
```

---

## Production Deployment

### 1. Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Code review approved
- [ ] Staging deployment successful
- [ ] Database backups completed
- [ ] Rollback plan prepared
- [ ] Team notified
- [ ] Maintenance window scheduled

### 2. Backup Current State

```bash
# Backup Redis data
docker exec enterprise-ai-redis redis-cli SAVE
docker cp enterprise-ai-redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d-%H%M%S).rdb

# Backup configuration
cp .env .env.backup-$(date +%Y%m%d-%H%M%S)
```

### 3. Deploy New Version

```bash
# Pull latest code
git fetch origin
git checkout main
git pull origin main

# Build production image
docker build -t enterprise-ai-backend:latest -f backend/Dockerfile backend/

# Tag with version
docker tag enterprise-ai-backend:latest enterprise-ai-backend:v1.0.0

# Stop current services
docker-compose down

# Start new services
docker-compose up -d

# Wait for startup
sleep 15
```

### 4. Post-Deployment Verification

```bash
# Check health
curl http://production-server:8000/health

# Check logs for errors
docker-compose logs --tail=100 backend | grep ERROR

# Monitor metrics
# (Check Grafana/Prometheus dashboards)

# Test critical paths
./scripts/smoke-tests.sh
```

### 5. Monitor for Issues

```bash
# Watch logs in real-time
docker-compose logs -f backend

# Monitor error rate
# (Check monitoring dashboard)

# Check response times
# (Check APM tool)
```

---

## Rollback Procedures

### Quick Rollback (< 5 minutes)

```bash
# Stop current version
docker-compose down

# Restore previous image
docker tag enterprise-ai-backend:v0.9.0 enterprise-ai-backend:latest

# Start previous version
docker-compose up -d

# Verify health
curl http://production-server:8000/health
```

### Full Rollback (< 15 minutes)

```bash
# 1. Stop services
docker-compose down

# 2. Restore Redis backup
docker cp ./backups/redis-YYYYMMDD-HHMMSS.rdb enterprise-ai-redis:/data/dump.rdb
docker-compose up -d redis
docker exec enterprise-ai-redis redis-cli SHUTDOWN SAVE
docker-compose up -d redis

# 3. Restore configuration
cp .env.backup-YYYYMMDD-HHMMSS .env

# 4. Checkout previous version
git checkout v0.9.0

# 5. Rebuild and start
docker-compose build
docker-compose up -d

# 6. Verify
curl http://production-server:8000/health
```

---

## Troubleshooting

### Issue: Redis Connection Failed

**Symptoms:**

- Health check shows Redis as "unhealthy"
- Cache statistics show "disabled"
- Logs show "Redis unavailable"

**Solution:**

```bash
# Check Redis status
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Verify connection
docker exec enterprise-ai-redis redis-cli ping
# Expected: PONG

# Check Redis memory
docker exec enterprise-ai-redis redis-cli INFO memory
```

### Issue: High Memory Usage

**Symptoms:**

- Backend container using >2GB memory
- Slow response times
- OOM errors in logs

**Solution:**

```bash
# Check memory usage
docker stats enterprise-ai-backend

# Clear cache
curl -X POST http://localhost:8000/api/cache/clear

# Restart backend
docker-compose restart backend

# Check for memory leaks
docker exec enterprise-ai-backend python -m memory_profiler src/main.py
```

### Issue: Rate Limiting Not Working

**Symptoms:**

- No rate limit headers in responses
- Unlimited requests allowed
- Logs show "Rate limiting disabled"

**Solution:**

```bash
# Check Redis connection
curl http://localhost:8000/health | jq '.components.redis'

# Verify environment variable
docker exec enterprise-ai-backend env | grep ENABLE_RATE_LIMITING

# Check rate limiter initialization
docker-compose logs backend | grep "Rate limiter"

# Restart with rate limiting enabled
docker-compose down
ENABLE_RATE_LIMITING=true docker-compose up -d
```

### Issue: Slow LLM Responses

**Symptoms:**

- Response times >5 seconds
- Cache hit rate <10%
- High CPU usage

**Solution:**

```bash
# Check cache statistics
curl http://localhost:8000/health | jq '.components.cache'

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check Ollama model
docker exec ollama ollama list

# Pull faster model
docker exec ollama ollama pull llama3.2:3b

# Update model in config
# Edit .env: OLLAMA_MODEL=llama3.2:3b

# Restart backend
docker-compose restart backend
```

---

## Monitoring

### Key Metrics to Monitor

#### Application Metrics

- **Request Rate**: Requests per second
- **Response Time**: p50, p95, p99 latencies
- **Error Rate**: 4xx and 5xx responses
- **Cache Hit Rate**: Percentage of cache hits
- **Active Connections**: WebSocket connections

#### Infrastructure Metrics

- **CPU Usage**: Backend container CPU %
- **Memory Usage**: Backend container memory
- **Redis Memory**: Redis memory usage
- **Disk Usage**: Log and data disk usage

#### Business Metrics

- **LLM Calls**: Total LLM API calls
- **Cache Savings**: Requests served from cache
- **Rate Limit Hits**: Requests rate limited
- **Agent Usage**: Requests per agent type

### Monitoring Tools

#### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Cache hit rate
rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])

# Response time p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

#### Log Queries

```bash
# Error logs in last hour
docker-compose logs --since 1h backend | grep ERROR

# Slow requests (>1s)
docker-compose logs backend | grep "duration_ms" | awk '$NF > 1000'

# Rate limit hits
docker-compose logs backend | grep "Rate limit exceeded"

# Cache statistics
docker-compose logs backend | grep "Cache hit"
```

### Alert Thresholds

| Metric              | Warning | Critical |
| ------------------- | ------- | -------- |
| Error Rate          | >1%     | >5%      |
| Response Time (p95) | >2s     | >5s      |
| CPU Usage           | >70%    | >90%     |
| Memory Usage        | >80%    | >95%     |
| Cache Hit Rate      | <20%    | <10%     |
| Redis Memory        | >80%    | >95%     |

---

## Maintenance

### Daily Tasks

- [ ] Check error logs
- [ ] Review monitoring dashboards
- [ ] Verify backup completion
- [ ] Check disk space

### Weekly Tasks

- [ ] Review performance metrics
- [ ] Analyze cache hit rates
- [ ] Check for security updates
- [ ] Review rate limit statistics

### Monthly Tasks

- [ ] Update dependencies
- [ ] Review and optimize queries
- [ ] Capacity planning review
- [ ] Security audit

### Quarterly Tasks

- [ ] Major version updates
- [ ] Performance testing
- [ ] Disaster recovery drill
- [ ] Architecture review

---

## Emergency Contacts

**On-Call Engineer:** [Your Team]
**Escalation:** [Manager]
**Infrastructure:** [DevOps Team]

---

## Useful Commands

### Docker Commands

```bash
# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart backend

# Scale service
docker-compose up -d --scale backend=3

# Execute command in container
docker-compose exec backend python -c "print('test')"

# View resource usage
docker stats
```

### Redis Commands

```bash
# Connect to Redis
docker exec -it enterprise-ai-redis redis-cli

# Check memory
INFO memory

# Get cache keys
KEYS llm_cache:*

# Clear cache
FLUSHDB

# Monitor commands
MONITOR
```

### Health Check Commands

```bash
# Quick health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health | jq

# Check specific component
curl http://localhost:8000/health | jq '.components.redis'
```

---

**Project Creator:** Herman Swanepoel
**Document Version:** 1.0
**Last Updated:** 2025-10-13
