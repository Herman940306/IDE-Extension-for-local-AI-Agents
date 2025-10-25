# AuraIA Local Deployment Test Plan

**Version:** 1.0 \
**Author:** Platform Engineering \
**Last Updated:** 2025-10-19

---

## Purpose

Execute a full local deployment rehearsal to validate the developer-focused workflow ahead of production rollout. This complements the Azure staging dry run by ensuring the repo can be brought online end-to-end using only local resources (PowerShell, Docker Desktop, Ollama).

---

## Preconditions

- Windows 11 workstation with PowerShell 7, Docker Desktop, and Ollama installed.
- Repository cloned at `E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code`.
- `.env.production` seeded with non-production secrets (compatible with local stack). Use `backend\env.example` as baseline.
- Python 3.11 added to `PATH`; Node.js 18+ available.
- Optional: WSL2 disabled for Docker if Hyper-V conflicts are observed.

---

## Test Matrix

| Area                  | Goal                                                                       | Tools                                                 |
| --------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------- |
| Backend runtime       | Validate FastAPI service with reload and background workers                | PowerShell, Python 3.11                               |
| Docker stack          | Validate Compose environment (backend, Prometheus, Grafana, Redis, Ollama) | Docker Desktop _(optional – see Dockerless fallback)_ |
| Extension integration | Validate VSIX against local backend                                        | VS Code, aura-ai-assistant-1.0.0.vsix                 |
| Quality gates         | Ensure `pytest`, `black`, `flake8`, secret scan execute locally            | PowerShell                                            |
| Monitoring            | Confirm Prometheus targets/alerts, inspect Grafana dashboard               | Browser, Prometheus UI                                |

---

## Execution Steps

1. **Bootstrap Environment**

   ```powershell
   cd "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
   python -m venv backend\.venv_new
   backend\.venv_new\Scripts\activate
   pip install --upgrade pip
   pip install -r backend\requirements.txt
   ```

2. **Run Backend Locally**

   ```powershell
   cd backend
   ..\.venv_new\Scripts\activate
   python run.py
   ```

   - Validate `/docs` and `/health` at `http://localhost:8001`.
   - Capture logs: `logs/local-deploy/backend-YYYYMMDD-HHMM.log`.

3. **Execute Quality Gates**

   ```powershell
   pytest backend/tests -v
   black backend --line-length 100 --check
   flake8 backend
   ```

   - Note command durations; any failure blocks test.

4. **(Optional) Start Docker Compose Stack**

   ```powershell
   cd ..
   copy backend\env.example backend\.env.production
   docker compose up -d --build
   docker compose ps
   ```

   - Verify services reachable:
     - Backend `http://localhost:8001`
     - Prometheus `http://localhost:9090`
     - Grafana `http://localhost:3000`
     - Ollama `http://localhost:11434`

   _Skip this step if Docker Desktop is unavailable and follow the Dockerless fallback below._

5. **Extension Validation**

   ```powershell
   cd extension
   npm ci
   npm run compile
   npm run package
   ```

   - Install VSIX in VS Code (Extensions → ⋯ → Install from VSIX).
   - Set `aura.backend.url` to `http://localhost:8001`.
   - Smoke commands: inline suggestion, AI code action, status bar update.

6. **Monitoring & Alert Test**
   - Visit Grafana dashboard `AuraIA/Local` (import from `monitoring/grafana-local.json` if absent).
   - Create temporary alert rule or trigger existing latency alert by throttling backend (e.g., stop service and observe `AuraIABackendDown`).
   - Document alert receipt (email or Teams message).

7. **Secret Scanning Drill**

   ```powershell
   gh workflow run secret-scan.yml
   ```

   - Alternatively run locally: `gitleaks detect --config .gitleaks.toml`.
   - Record results in `logs/local-deploy/secret-scan-YYYYMMDD.txt`.

8. **Teardown**

   ```powershell
   docker compose down --volumes   # only if compose was started
   deactivate
   ```

   - Clean up logs older than 14 days.

---

## Success Criteria

- Backend serves `/health` and `/docs` when run both manually and via Docker Compose.
  - If Docker Desktop is unavailable, document manual backend run plus any auxiliary services started via fallback scripts.
- Quality gates pass without modifications.
- Extension connects to local backend; commands return responses without errors.
- Grafana dashboard shows all targets `UP`; alerting path verified.
  - For Dockerless run, note which monitoring components (if any) were substituted or skipped.
- Secret scanning workflow completes successfully (no leaks detected).
- All steps documented with timestamps in `logs/local-deploy/2025-10-19-local-test.md`.

---

## 2025-10-19 Dockerless Dry Run Results

| Step                      | Status | Notes                                                                                                                                           |
| ------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Virtualenv & dependencies | ✅     | Created `backend/.venv_new`, installed `backend/requirements.txt` plus `pydantic-settings`, `cryptography`, `structlog`, `dependency-injector`. |
| Redis bootstrap           | ✅     | `setup-redis.bat` installed service; `Get-Service Redis` reports **Running**.                                                                   |
| Backend runtime           | ✅     | `python run.py` reports _Application startup complete_; `/health` returns `healthy`.                                                            |
| Quality gates             | ✅     | `pytest backend/tests -v` passes after configuration fixes (black/flake8 not run this pass).                                                    |
| Docker Compose            | ➖     | Skipped for dockerless rehearsal.                                                                                                               |
| Monitoring drill          | ➖     | Prometheus/Grafana skipped; documented reliance on `/health` checks in log.                                                                     |
| Secret scanning           | ✅     | `gitleaks detect --config .gitleaks.toml` → no leaks found.                                                                                     |
| VSIX smoke test           | ✅     | VSIX packaged/installed; inline suggestion + code action succeed vs local backend.                                                              |

---

## Reporting Template

Use `logs/local-deploy/2025-10-19-local-test.md` to record:

- Start/End time
- Operator
- Step-by-step outcomes
- Metrics (latency, CPU/memory snapshots)
- Issues encountered & resolution
- Follow-up actions (if any)

---

## Follow-Up Actions

- Schedule local deployment test quarterly or before major releases.
- Integrate smoke script with local run (`scripts/smoke_tests.py --env local`).
- Consider adding GitHub Action job that simulates critical portions via `act` or containerized test harness.
- Document Dockerless runbooks and keep `setup-redis.bat`/`START_BACKEND.bat` instructions current.

---

## Dockerless Fallback Workflow

If Docker Desktop cannot be used:

1. **Redis & Vector Store**
   - Run `setup-redis.bat` from the repository root to install/start a local Redis instance (defaults to `redis://localhost:6379`).
   - Ensure `CHROMA_PERSIST_DIR` points to `data/chroma` (local filesystem persistence).

2. **Backend + Monitoring**
   - Launch backend via provided script: `START_BACKEND.bat` (invokes virtualenv + `python run.py`).
   - Optional: run `monitor/monitor.py` for lightweight health logging if Grafana is unavailable.

3. **Observability Substitutes**
   - Use `backend/tools/tail_logs.py` (or PowerShell `Get-Content -Wait`) to monitor JSON logs.
   - Trigger manual health loop: `while ($true) { Invoke-WebRequest http://localhost:8001/health; Start-Sleep 30 }`.

4. **Extension Validation**
   - Same as primary plan: package/install VSIX, point `aura.backend.url` to `http://localhost:8001`.

5. **Alert Simulation**
   - Without Prometheus/Grafana, simulate alert escalation by intentionally stopping Redis and verifying backend logs raise `redis_unavailable` warnings; capture timestamps for the report.

6. **Teardown**
   - Stop backend (`Ctrl+C`), run `redis-cli shutdown` if the Windows service is active, and deactivate the virtualenv.
