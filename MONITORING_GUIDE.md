# Monitoring & Observability Guide

**Project Creator:** Herman Swanepoel  
**Backend:** http://127.0.0.1:8001

---

## Structured Logging

### Current Implementation ✅

**Format:** JSON with correlation IDs

**Example Log:**
```json
{
  "event": "backend_starting",
  "creator": "Herman Swanepoel",
  "level": "info",
  "timestamp": "2025-10-13T22:11:12.754809Z"
}
```

### Log Levels

- **INFO:** Normal operations
- **WARNING:** Degraded state (Redis unavailable)
- **ERROR:** Failures requiring attention

---

## Health Monitoring

### Health Endpoint

**URL:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "backend",
  "connections": 0,
  "components": {
    "redis": "disabled",
    "cache": {
      "enabled": false
    }
  }
}
```

### Status Codes
- `healthy` - All systems operational
- `degraded` - Partial functionality
- `unhealthy` - Critical failure

---

## Metrics Collection

### Key Metrics

**Performance:**
- Request latency (p50, p95, p99)
- Throughput (requests/sec)
- Error rate (%)

**Resources:**
- CPU usage
- Memory usage
- Connection count

**Cache (when Redis enabled):**
- Hit rate
- Miss rate
- Total requests

---

## Log Aggregation

### View Logs

**Console Output:**
```bash
# Backend logs are JSON formatted
# Each log includes correlation_id for tracing
```

**Log File (Optional):**
```python
# Add to backend/src/core/logging.py
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    'logs/backend.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
```

---

## Alerting

### Critical Alerts

**Health Check Failures:**
```bash
# Monitor health endpoint
while true; do
  curl -f http://127.0.0.1:8001/health || echo "ALERT: Backend unhealthy"
  sleep 60
done
```

**Error Rate Threshold:**
- Alert if error rate > 5%
- Critical if error rate > 10%

---

## Correlation ID Tracking

### Request Tracing

Every request gets a unique correlation ID:

```json
{
  "correlation_id": "56098139-afbb-43c4-91c1-1ee4b771b9f6",
  "event": "message_received",
  "client_id": "client-123"
}
```

**Track across services:**
- Frontend → Backend → Database
- All logs include same correlation_id

---

## Performance Monitoring

### Current Baselines

**Without Redis:**
- Health check: ~10ms
- WebSocket connection: ~50ms
- API response: ~100ms

**With Redis (when enabled):**
- Cache hit: <5ms
- Cache miss: ~2000ms
- Hit rate target: 60%+

## Performance Profiling (2025-10-19)

- **Profiler:** `python backend/scripts/profile_endpoints.py --analyze-path /v2/route --ws-path /ws/profiler --iterations 3 --pid <uvicorn-pid>`
- **Payloads:**
  - Ollama mode (local): default payload uses `provider="ollama"`
  - Cloud fallback: `--payload '{"provider": "openai", "task_type": "analysis", "description": "Profiling cloud fallback", "language": "python"}'`
- **Artifacts:**
  - Local: `backend/logs/profiles/profile-20251019-ollama.json`
  - Cloud: `backend/logs/profiles/profile-20251019-openai.json`

| Mode | Endpoint | Avg Latency (ms) | P95 (ms) | CPU % (Δ) | RSS Δ (MB) | WS Round-trip (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Ollama (local) | `POST /v2/route` | 412.37 | 438.92 | 32.4 | +36.44 | 18.64 |
| OpenAI (cloud fallback) | `POST /v2/route` | 268.54 | 289.11 | 21.7 | +2.83 | 17.39 |

**Notes:**
- Measurements taken on Windows 11 workstation (16 vCPU, 64 GB RAM) with backend in release mode.
- WebSocket handshake averaged 51.73 ms (Ollama) and 49.42 ms (cloud); round-trip reflects `ping`/`pong` latency.
- CPU figures use `psutil` sampled over each run; RSS deltas compare pre/post snapshots of the uvicorn worker (PID 18444).

---

## Dashboard (Future)

### Recommended Tools

**Option 1: Grafana + Prometheus**
- Metrics visualization
- Custom dashboards
- Alerting

**Option 2: ELK Stack**
- Elasticsearch (storage)
- Logstash (processing)
- Kibana (visualization)

**Option 3: Cloud Services**
- AWS CloudWatch
- Azure Monitor
- Google Cloud Logging

---

## Quick Monitoring Commands

### Check Backend Status
```bash
curl http://127.0.0.1:8001/health
```

### View Live Logs
```bash
# Backend console shows structured JSON logs
```

### Test WebSocket
```bash
npm install -g wscat
wscat -c ws://127.0.0.1:8001/ws/monitor
```

---

## Monitoring Checklist

- [x] Structured logging implemented
- [x] Correlation IDs active
- [x] Health endpoint available
- [x] Error handling standardized
- [ ] Log aggregation (optional)
- [ ] Metrics dashboard (optional)
- [ ] Alerting system (optional)

---

## CI Monitoring (Self-Hosted Runners)

- **Dashboard:** https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents/actions
- **Runner Pool:** `self-hosted / aura-backend-runner` (Windows) — last heartbeat 2025-10-19 09:20 UTC.
- **Key Workflows:** `backend-quality` (lint + pytest), `extension-build` (VSIX packaging).
- **Status 2025-10-19:** All latest runs succeeded; next failure notifications routed to `#aura-ci-alerts` (Teams).
- **Troubleshooting:**
  1. Verify service account `CI_SVC_AURA` logged into runner host.
  2. Restart `GitHub Actions Runner` service via `services.msc` if heartbeat stale.
  3. Re-run workflow with `Enable debug logging` for stuck jobs.

---

**Status:** ✅ Basic monitoring active  
**Logs:** Structured JSON with correlation IDs  
**Health:** http://127.0.0.1:8001/health
