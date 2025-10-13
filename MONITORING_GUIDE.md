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

**Status:** ✅ Basic monitoring active  
**Logs:** Structured JSON with correlation IDs  
**Health:** http://127.0.0.1:8001/health
