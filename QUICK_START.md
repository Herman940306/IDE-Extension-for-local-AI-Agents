# AuraIA Quick Start Guide

**Last Updated:** 2025-10-19  \
**Maintainer:** Platform Engineering

---

## Environment Options

| Scenario | Path | Notes |
|----------|------|-------|
| Daily development | Local virtual environment | Fast iteration with hot reload (`run.py`). |
| Team validation | Docker Compose | Launches backend, Redis, Ollama, Prometheus, Grafana. |
| Production rollout | Azure Container Apps | Follow `PRODUCTION_DEPLOYMENT_GUIDE.md` for provisioning. |

---

## Local Development Workflow

1. Activate the virtual environment:
   ```powershell
   cd backend
   ..\\.venv_new\\Scripts\\activate
   ```
2. Ensure Ollama is running:
   ```powershell
   ollama serve
   ```
3. Start the backend API:
   ```powershell
   python run.py
   ```
4. Verify endpoints:
   - Swagger UI: <http://localhost:8001/docs>
   - Health check: <http://localhost:8001/health>

**Common commands**
```powershell
pytest backend/tests -v            # 411 passed / 5 skipped (2025-10-19)
black backend --line-length 100
flake8 backend
```

---

## Docker Compose Stack

From the repository root:
```powershell
copy backend\\env.example backend\\.env.production   # populate with Key Vault secrets first
docker compose up -d --build
docker compose logs -f backend
```

Services:
- Backend API → <http://localhost:8001>
- Prometheus → <http://localhost:9090>
- Grafana → <http://localhost:3000> (`GF_SECURITY_ADMIN_*` credentials)
- Ollama → <http://localhost:11434>

Stop the stack with `docker compose down`.

---

## VS Code Extension Flow

1. Install dependencies:
   ```powershell
   cd extension
   npm ci
   ```
2. Compile and package:
   ```powershell
   npm run compile
   npm run package   # aura-ai-assistant-1.0.0.vsix
   ```
3. Install the VSIX via VS Code (`Extensions` → `...` → `Install from VSIX`).
4. Configure settings: set `aura.backend.url` to your backend URL and leave `enterpriseAI.privacy.allowTelemetry` disabled unless explicitly approved.

---

## Secrets and Configuration

- Populate `backend/.env.production` and Azure Container Apps secrets per `PRODUCTION_DEPLOYMENT_GUIDE.md`.
- Required values: `SECRET_KEY`, `ENCRYPTION_KEY`, `DB_REDIS_URL`, `OLLAMA_BASE_URL`, `CHROMA_PERSIST_DIR`.
- `.gitleaks.toml` and the `secret-scan.yml` workflow enforce secret hygiene on every PR, push, and nightly schedule.

---

## Monitoring and Recovery

- Prometheus loads alert rules from `monitoring/alerts.yml` (backend availability, Redis availability, 5xx error rates).
- Disaster recovery procedures covering Redis and Chroma live in `SYSTEM_RECOVERY.md`.
- Privacy posture and retention policies are recorded in `PRIVACY_COMPLIANCE.md`; threat model details reside in `SECURITY_THREAT_MODEL.md`.

---

## Verification Checklist

- [ ] Backend health endpoint returns `healthy`.  \
- [ ] Extension commands reach backend successfully.  \
- [ ] Prometheus targets report `UP` (compose or cloud).  \
- [ ] Secret scanning workflow is green on the latest commit.  \
- [ ] Optional: `pytest backend/tests -v` passes locally.

---

## Next Steps

- Review `PRODUCTION_DEPLOYMENT_GUIDE.md` for Azure Container Apps rollout guidance.  \
- Consult `MONITORING_GUIDE.md` to configure alert routing and on-call rotations.  \
- Track remaining Phase 5 work items in `TASK.md`.

Need assistance? Reach out via the #aura-ops channel or open a repository issue.
