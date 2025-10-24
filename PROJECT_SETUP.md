# AuraIA Project Setup Guide

**Maintainer:** Platform Engineering \
**Initial Author:** Herman Swanepoel \
**Last Updated:** 2025-10-19

---

## Purpose

This guide takes a new engineer from a clean machine to a productive AuraIA development environment. Keep `QUICK_START.md` handy for the short checklist and consult `PRODUCTION_DEPLOYMENT_GUIDE.md` when targeting Azure Container Apps.

---

## Prerequisites

- Python 3.11+ available on `PATH` (use the `python` launcher on Windows).
- Node.js 18+ with npm.
- Git and VS Code (install the Python, Pylance, and ESLint extensions).
- Docker Desktop (required for the integration stack).
- Ollama (for local LLM inference; optional for server-side only development).

> **Tip:** Enable hardware virtualisation (BIOS/UEFI) so Docker and Ollama can start.

---

## Repository Layout

```
AI Agents Integration system for VS Code/
├── backend/              # FastAPI + agent orchestration service
│   ├── requirements.txt
│   ├── run.py            # Dev entry point
│   └── tests/
├── extension/            # VS Code extension
│   ├── src/
│   ├── package.json
│   └── tsconfig.json
├── monitoring/           # Prometheus/Grafana configuration
├── scripts/              # Automation helpers
├── docker-compose.yml    # Local integration environment
└── docs/                 # Architecture, compliance, security references
```

Essential docs: `MONITORING_GUIDE.md`, `SECURITY_THREAT_MODEL.md`, `PRIVACY_COMPLIANCE.md`, `PRODUCTION_DEPLOYMENT_GUIDE.md`.

---

## Bootstrap Sequence

### Windows PowerShell

```powershell
cd "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
cd backend
python -m venv ..\.venv_new
..\.venv_new\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
ollama serve  # optional, runs in foreground
```

### macOS / Linux

```bash
cd ~/workspace/AI-Agents-Integration
cd backend
python3.11 -m venv ../.venv_new
source ../.venv_new/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
ollama serve  # optional
```

> The shared `.venv_new/` lives beside `backend/` to keep IDE interpreter settings consistent with the quick start guide.

---

## Backend Development Loop

1. Activate the environment:
   ```powershell
   cd backend
   ..\.venv_new\Scripts\activate
   ```
2. Start the API with live reload:
   ```powershell
   python run.py
   ```
3. Verify endpoints:
   - Swagger UI → <http://localhost:8001/docs>
   - Health check → <http://localhost:8001/health>
4. Run quality gates before committing:
   ```powershell
   pytest backend/tests -v
   black backend --line-length 100
   flake8 backend
   ```

Logs land in `logs/backend/`; adjust verbosity through environment variables in `backend/config/settings.py`.

---

## Extension Development Loop

```powershell
cd extension
npm ci
npm run compile
npm run package   # aura-ai-assistant-1.0.0.vsix
```

Install the `.vsix` via VS Code (`Extensions` → `⋯` → `Install from VSIX`). Set `aura.backend.url` to your backend endpoint and leave `enterpriseAI.privacy.allowTelemetry` disabled unless legal approval is filed.

---

## Docker Compose Environment

From the repository root:

```powershell
copy backend\env.example backend\.env.production  # edit with secrets
docker compose up -d --build
docker compose logs -f backend
```

Exposed services:

- Backend API → <http://localhost:8001>
- Prometheus → <http://localhost:9090>
- Grafana → <http://localhost:3000>
- Ollama API → <http://localhost:11434>

Shut down with `docker compose down`. Append `--volumes` to reset Redis and Chroma state.

---

## Secrets & Compliance

- Populate `backend/.env.production` (and Azure Container Apps secrets) with `SECRET_KEY`, `ENCRYPTION_KEY`, `DB_REDIS_URL`, `OLLAMA_BASE_URL`, `CHROMA_PERSIST_DIR`.
- Optional LLM fallbacks: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_OPENAI_ENDPOINT`.
- Secret scanning is enforced by `.gitleaks.toml` and `.github/workflows/secret-scan.yml`; follow the incident response steps in `MONITORING_GUIDE.md` if a leak is detected.

---

## Verification Checklist

- [ ] `pytest backend/tests -v` passes.
- [ ] `black backend --line-length 100` yields no changes.
- [ ] `flake8 backend` reports no violations.
- [ ] Extension connects to the backend and returns completions.
- [ ] Secret scan workflow is green on the latest push.

Mirror these states in `TASK.md` and `IMPLEMENTATION_PROGRESS.md` as you progress.

---

## Troubleshooting

**Virtual environment will not activate** \
Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` once, then reopen PowerShell.

**Port 8001 already in use** \
Use `Get-NetTCPConnection -LocalPort 8001 | Stop-Process -Id {$_.OwningProcess}` or change the port via `backend/.env`.

**Ollama requests hang** \
Ensure `ollama serve` is running and the referenced model is installed. See fallback guidance in `MONITORING_GUIDE.md`.

**Secret scan failure** \
Rotate the leaked value, scrub commit history if necessary, and document the incident per `MONITORING_GUIDE.md`.

---

## Next Steps

1. Read `ARCHITECTURE_V2_NEXTGEN.md` for updated component diagrams.
2. Align with the operator flow in `QUICK_START.md`.
3. Review remaining Phase 5 tasks in `TASK.md`.
4. Coordinate with security for the staged deployment dry run.

Questions? Reach out in the `#aura-ops` channel or file a GitHub issue tagged `onboarding`.
