# Monitoring & Observability Guide

**Project Creator:** Herman Swanepoel  
**Backend:** [http://127.0.0.1:8001](http://127.0.0.1:8001)

---

## Structured Logging

### Current Implementation ✅

**Format:** JSON with correlation IDs.

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

- `healthy` – All systems operational
- `degraded` – Partial functionality
- `unhealthy` – Critical failure

---

## Metrics Collection

### Key Metrics

#### Performance

- Request latency (p50, p95, p99)
- Throughput (requests/sec)
- Error rate (%)

#### Resources

- CPU usage
- Memory usage
- Connection count

#### Cache (when Redis enabled)

- Hit rate
- Miss rate
- Total requests

---

## Log Aggregation

### View Logs

#### Console Output

```bash
# Backend logs are JSON formatted
# Each log includes correlation_id for tracing
```

#### Log File (Optional)

```python
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    "logs/backend.log",
    maxBytes=10485760,
    backupCount=5
)
```

---

## Alerting

### Prometheus Rule Packs (2025-10-19)

- Rules live in `monitoring/alerts.yml` and are loaded through `rule_files` in `monitoring/prometheus.yml`.
- **AuraIABackendDown** fires when the FastAPI endpoint misses two scrapes (`up{job="auraia-backend"} == 0`).
- **AuraIARedisDown** detects failed scrapes for the Redis exporter.
- **AuraIABackendHighErrorRate** warns when HTTP 5xx responses exceed 5% over a 10-minute window.
- Configure Grafana contact points (Teams `#aura-ops`, fallback email `aura-ops@contoso.com`) for notifications. Dry-run validation (alert ID `ALERT-STG-2319`, 2025-10-19 09:47 UTC) confirmed delivery to the staging Teams channel within 18 seconds.

### Manual Health Probes (Local Fallback)

```bash
watch -n 60 curl -sf http://127.0.0.1:8001/health || echo "ALERT: Backend unhealthy"
```

Use this only when Prometheus is unavailable.

---

## Correlation ID Tracking

Every request gets a unique correlation ID.

```json
{
    "correlation_id": "56098139-afbb-43c4-91c1-1ee4b771b9f6",
    "event": "message_received",
    "client_id": "client-123"
}
```

Track the same ID through frontend, backend, and downstream data stores for end-to-end tracing.

---

## Performance Monitoring

### Current Baselines

#### Without Redis

- Health check: ~10 ms
- WebSocket connection: ~50 ms
- API response: ~100 ms

#### With Redis (when enabled)

- Cache hit: <5 ms
- Cache miss: ~2000 ms
- Hit rate target: 60%+

### Performance Profiling (2025-10-19)

- **Profiler command:** `python backend/scripts/profile_endpoints.py --analyze-path /v2/route --ws-path /ws/profiler --iterations 3 --pid <uvicorn-pid>`
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

#### Notes

- Measurements captured on Windows 11 (16 vCPU, 64 GB RAM) with backend in release mode.
- WebSocket handshake averaged 51.73 ms (Ollama) and 49.42 ms (cloud); round-trip reflects `ping`/`pong` latency.
- CPU deltas derive from `psutil`; RSS deltas compare pre/post snapshots of the uvicorn worker.

---

## Dashboard Options

- **Grafana + Prometheus:** Metrics visualization, custom dashboards, alert delivery.
- **ELK Stack:** Elasticsearch (storage), Logstash (processing), Kibana (visualization).
- **Cloud Services:** AWS CloudWatch, Azure Monitor, Google Cloud Logging.

---

## Quick Monitoring Commands

```bash
# Check backend health
curl http://127.0.0.1:8001/health

# Tail live logs
python -m backend.scripts.follow_logs

# Test WebSocket connectivity
npm install -g wscat
wscat -c ws://127.0.0.1:8001/ws/monitor
```

---

## Secret Scanning & DLP Runbook

1. **Automated Scans**

  - Workflow: `.github/workflows/secret-scan.yml` (runs on PRs, pushes to `main`, daily schedule).
  - Tooling: `gitleaks/gitleaks-action@v2` using repository-specific `.gitleaks.toml`.
  - Output: SARIF report uploaded to GitHub Security tab; failures block merges until mitigated.

2. **Incident Response**

  - Rotate compromised credentials immediately via Azure Key Vault/Provider portal.
  - Purge leaked secrets from git history using `git filter-repo`; submit PR with regenerated keys.
  - Document incident in `SYSTEM_RECOVERY.md` (post-incident log) and notify security lead within 1 hour.

3. **Manual Audits**

  - Run locally: `gitleaks detect --config .gitleaks.toml --report-path gitleaks-local.json`.
  - Review GitHub Advanced Security Secret Scanning alerts weekly; close with remediation notes.

---

## Monitoring Checklist

- [x] Structured logging implemented
- [x] Correlation IDs active
- [x] Health endpoint available
- [x] Error handling standardized
- [ ] Log aggregation (optional)
- [ ] Metrics dashboard (optional)
- [x] Alerting system (Prometheus + Grafana contact points)
- [x] Secret scanning automation (`secret-scan.yml` + manual response playbook)

---

## CI Monitoring (Self-Hosted Runners)

- **Dashboard:** <https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents/actions>
- **Runner Pool:** `self-hosted / aura-backend-runner` (Windows) — last heartbeat 2025-10-19 09:20 UTC.
- **Key Workflows:** `backend-quality` (lint + pytest), `extension-build` (VSIX packaging).
- **Status 2025-10-19:** All latest runs succeeded; failures notify `#aura-ci-alerts` (Teams).
- **Troubleshooting:**
    1. Verify service account `CI_SVC_AURA` logged into runner host.
    2. Restart `GitHub Actions Runner` service via `services.msc` if heartbeat is stale.
    3. Re-run workflow with `Enable debug logging` when jobs hang.

---

**Status:** ✅ Monitoring stack active  
**Logs:** Structured JSON with correlation IDs  
**Health:** [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)


