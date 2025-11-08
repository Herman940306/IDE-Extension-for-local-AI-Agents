# Operations Playbook

This playbook is the day-to-day guide for operating the local AI Agents stack (FastAPI backend, Redis, Prometheus, Grafana, Caddy reverse proxy, optional Ollama). It favors quick fixes and verified commands.

- Primary endpoints (via Caddy)
  - API: https://localhost/api
  - Backend health: https://localhost/api/health
  - Grafana: https://localhost/grafana
  - Prometheus: https://localhost/prometheus

- Source of truth (as-code)
  - Docker Compose: `docker-compose.yml`
  - Grafana provisioning:
    - Datasource: `monitoring/provisioning/datasources/datasource.yml`
    - Alerting: `monitoring/provisioning/alerting/*.yml`
  - Backend image: `backend/Dockerfile`

- Current alerting posture
  - Active: `smoke_test_email` (info) — synthetic smoke alert for email pipeline validation.
  - Removed: legacy `smoke_test` rule (previously paused) to eliminate noise.
  - Routing: default receiver `email-default`; no webhook routes (by design).
  - Prometheus datasource URL includes route prefix `/prometheus` (critical).

---

## 1) Steady-state operations

### 1.1 Quick health checks (60 seconds)

- Backend via Caddy
  - GET https://localhost/api/health → expect JSON with status OK.
- Grafana API
  - GET https://localhost/grafana/api/health → expect database: ok and version.
- Prometheus readiness
  - GET https://localhost/prometheus/-/ready → expect "Prometheus Server is Ready.".

### 1.2 Dashboard pointers

- Grafana → Explore or dashboards for:
  - Prometheus: scrape targets and TSDB health.
  - Backend: request rate, latency, and `GET /metrics` exposure.
  - Redis: connection metrics if exported (optional).

### 1.3 Useful container commands (PowerShell)

```powershell
# List services
docker compose ps

# Tail logs (replace <svc> with grafana|prometheus|backend|caddy|redis|ollama)
docker compose logs <svc> -f --since 5m

# Restart a service (e.g., grafana)
docker compose restart grafana

# If you prefer container names (what you see in 'docker ps')
docker logs -f --since=5m <container-name>
docker restart <container-name>
```

---

## 2) Alerts and on-call

### 2.1 Rules overview

- File: `monitoring/provisioning/alerting/alert-rules.yml`
- Active rule `smoke_test_email` uses query `sum(up) > 0` with a 10-minute lookback window; it is informational and verifies email delivery.

### 2.2 Toggling the smoke email rule

- To pause temporarily: set `isPaused: true` for the `smoke_test_email` rule, then restart Grafana.
- To remove entirely: delete the rule block and restart Grafana.
- To flip to "fires-on-failure" (recommended for ongoing operation):
  - Change the expression to `sum(up) == 0` and keep `isPaused: false`.

```powershell
# Apply provisioning changes
docker compose restart grafana

# Verify only desired rules are active
docker compose logs grafana -f --since 2m | findstr /I "rule_uid="
```

### 2.3 Notification policies

- File: `monitoring/provisioning/alerting/notification-policies.yml`
- Default route: `email-default` only. Add webhook routes later if needed.

### 2.4 Known historical alert: DatasourceError (resolved)

- Symptom: Grafana alerts show `DatasourceError` with 404s.
- Root cause: Prometheus ran with `--web.route-prefix=/prometheus` but datasource URL missed the prefix.
- Fix: `monitoring/provisioning/datasources/datasource.yml` → `url: http://prometheus:9090/prometheus`.

---

## 3) Incident response

### 3.1 First 15 minutes

1) Scope impact
- Which endpoints fail? `/api`, `/grafana`, `/prometheus`.
2) Check logs
- `docker compose logs <svc> -f --since 10m`
3) Look for recent changes
- Git diff and provisioning edits; any image rebuilds.
4) Stabilize
- Roll back the last change or restart only the failing service.

### 3.2 Common incidents and quick fixes

- Grafana restart loop due to invalid alert rule time range
  - Ensure each rule has a valid `relativeTimeRange` (from > 0, to >= 0) and explicit datasource uid.
  - Restart Grafana.

- Email not received
  - Check Grafana logs for notifier errors; ensure notification policy routes default to `email-default`.
  - Verify SMTP env is set for Grafana container.

- Backend restart loop (GitPython error)
  - Ensure `git` is installed in the runtime image (`backend/Dockerfile`). Rebuild image if needed.

- Prometheus 404 from Grafana alerts
  - Confirm datasource URL contains `/prometheus` to match Prometheus `--web.route-prefix`.

### 3.3 Post-incident

- Record the cause, resolution, and one follow-up hardening action.
- Update this playbook if the fix reveals a new pitfall.

---

## 4) Maintenance and lifecycle

- Deploy/rollback
  - Use `docker compose up -d` after changes; prefer restarting only impacted services.

- Upgrades
  - Pin versions in Compose; upgrade one component at a time and verify health checks.

- Backups
  - Prefer provisioning-as-code for Grafana. If local dashboards are created in UI, export them or persist the Grafana storage volume.

- Capacity and retention
  - Adjust Prometheus scrape intervals/retention as needed; monitor container memory and CPU.

---

## 5) Security and compliance

- Secrets and credentials
  - Use `.env` and environment variables; never commit real secrets.
  - Grafana admin password: rotate and store securely.

- TLS and certificates
  - Caddy terminates TLS for localhost. For external deployments, reevaluate certificate sources and domains.

- Access control
  - Prefer non-admin Grafana accounts for daily viewing; restrict admin usage.

---

## 6) Reliability hygiene

- Provisioning checks
  - Validate YAML before restart; consider adding CI to lint provisioning files.

- Synthetic monitoring strategy
  - Long-term: change smoke alert to fire only on failure, and schedule a periodic email heartbeat test.

- Noise handling
  - Known benign Grafana warning: `xychart is already registered` — safe to ignore.

---

## 7) Appendix: Handy commands (pwsh)

```powershell
# Status
docker compose ps

# Logs (5 minutes)
docker compose logs grafana -f --since 5m

# Restart Grafana after provisioning edits
docker compose restart grafana

# Health checks via Caddy
curl -k https://localhost/api/health
curl -k https://localhost/grafana/api/health
curl -k https://localhost/prometheus/-/ready

# Look for alert rule activity (recent)
docker compose logs grafana -f --since 2m | findstr /I "rule_uid="
```

---

## 8) One-click ops script (pwsh)

Use the helper script at the repo root:

```powershell
# Default is health checks
./Ops-OneClick.ps1

# Explicit actions
./Ops-OneClick.ps1 -Action health           # API/Grafana/Prometheus probes
./Ops-OneClick.ps1 -Action stack-status     # docker compose ps
./Ops-OneClick.ps1 -Action alert-activity   # recent alert log activity
./Ops-OneClick.ps1 -Action restart-grafana  # apply provisioning changes

# Operate the smoke alert
./Ops-OneClick.ps1 -Action enable-smoke     # isPaused: false + restart
./Ops-OneClick.ps1 -Action disable-smoke    # isPaused: true  + restart
./Ops-OneClick.ps1 -Action mode-success     # expr: sum(up) > 0  + restart
./Ops-OneClick.ps1 -Action mode-failure     # expr: sum(up) == 0 + restart (recommended)
```

The script performs safe, targeted text edits in `monitoring/provisioning/alerting/alert-rules.yml` scoped to the `uid: smoke_test_email` rule, then restarts Grafana to apply.

---

## 9) Change history (this session)

---

## 10) Scheduled weekly heartbeat (GitHub Actions)

A workflow runs weekly to probe your deployed endpoints and open an issue if any check fails.

- Workflow: `.github/workflows/weekly-heartbeat.yml`
- Schedule: Mondays 09:00 UTC (and on manual dispatch)
- What it checks (via base URL):
  - `/api/health`
  - `/grafana/api/health`
  - `/prometheus/-/ready`

Configure it:

1) In GitHub → Settings → Variables → Repository Variables, set:
   - `HEARTBEAT_BASE_URL` to your public base URL (e.g., `https://example.com`).
   - Optional `HEARTBEAT_INSECURE` to `true` if you use self-signed TLS.
2) The run uploads `heartbeat_output.txt` as an artifact and opens an issue automatically on failure.

Notes:
- If `HEARTBEAT_BASE_URL` is not set or is `disabled`, the script exits successfully without probing.
- You can change the cron in the workflow to fit your schedule.

- Fixed email delivery by updating Grafana notification policies to email-only and correcting Prometheus datasource URL with `/prometheus`.
- Resolved backend restarts by installing `git` in runtime image.
- Removed legacy alert rule (`smoke_test`) and kept only `smoke_test_email` active.
- Verified service health via Caddy paths and Grafana logs.
