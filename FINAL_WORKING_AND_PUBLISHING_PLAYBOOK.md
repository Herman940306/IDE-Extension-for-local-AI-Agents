# Final Working and Publishing Playbook

Author: Herman Swanepoel
Repository: IDE-Extension-for-local-AI-Agents
Last updated: 2025-10-24

This one document is your end-to-end, copy-pasteable guide to get the system fully working locally, validate quality, deploy the backend, and publish the VS Code extension.

---

## 1) What’s already working (baseline)

- Python venv bound to VS Code tasks; no PATH issues.
- Dependencies install cleanly.
- Quality gates: Lint (Flake8), Format (Black), Type check (mypy) all PASS.
- Tests: 440 passed, 5 skipped (Ollama not available), coverage artifacts written (coverage.xml, htmlcov/).
- Tasks available in VS Code (use the venv’s python.exe):
  - Python: Install Dependencies
  - Python: Run Tests
  - Python: Test Coverage
  - Python: Lint with Flake8
  - Python: Format with Black
  - Python: Type Check (mypy)
  - Python: Run API (Uvicorn) → port 8001
- Docker stack present: Redis, Ollama, Backend, Prometheus, Grafana.
- Extension source under extension/ with packaging scripts and a .vsix artifact available.

Ports and URLs:

- Backend API: <http://127.0.0.1:8001>
- WebSocket: ws://127.0.0.1:8001/ws
- Ollama: <http://127.0.0.1:11434>
- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000>

---

## 2) Configure environment

Use these as a starting point; adjust for your machine.

- Local development: copy `backend/.env.example` to `backend/.env` and adjust.
- Container deployment: use `backend/.env.production` (already referenced by compose).

Minimum variables to confirm:

- OLLAMA_BASE_URL (ex: <http://localhost:11434>)
- REDIS_URL (ex: redis://localhost:6379)
- CHROMA_PERSIST_DIR (ex: ./data/chroma_db)
- SECRET_KEY, ENCRYPTION_KEY (set strong values in production)
- LOG_LEVEL (ex: INFO)

Optional for cloud fallback: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

---

## 3) Start everything with Docker Compose (recommended)

From repo root:

```powershell
# Start services
docker compose up -d

# Pull the models into the running Ollama container (examples)
docker exec -it $(docker ps -qf "name=ollama") ollama pull llama3.2:3b
docker exec -it $(docker ps -qf "name=ollama") ollama pull mistral:7b
```

Health checks:

- Backend: <http://127.0.0.1:8001/health>
- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000>

Volumes (data persists across restarts):

- redis_data, ollama_models, backend_state, backend_logs, prometheus_data, grafana_data

---

## 4) Or run the backend locally (no containers)

Prereqs: Redis and Ollama running locally (ports 6379, 11434).

```powershell
# In VS Code: run this task
#   Python: Run API (Uvicorn)
# It starts FastAPI from backend/ on port 8001 with reload.
```

Health checks:

- <http://127.0.0.1:8001/>
- <http://127.0.0.1:8001/health>

---

## 5) Try the VS Code extension locally

Install the packaged extension from extension/ (or build a fresh one):

```powershell
cd extension
npm ci
npm run package    # emits aura-ai-assistant-<version>.vsix
code --install-extension .\aura-ai-assistant-*.vsix
```

Configure in VS Code Settings:

- Backend URL: <http://127.0.0.1:8001>
- Backend WebSocket URL: ws://127.0.0.1:8001/ws

Exercise commands like “Aura: Generate Code”; watch backend logs for task flow.

---

## 6) Quality gates and checks (green-before-done)

Run these from VS Code tasks (powered by .venv) or the terminal.

```powershell
# Install deps (if needed)
& ".\.venv\Scripts\python.exe" -m pip install -r backend/requirements.txt

# Lint
& ".\.venv\Scripts\python.exe" -m flake8 backend

# Format
& ".\.venv\Scripts\python.exe" -m black backend --line-length=100

# Type check
& ".\.venv\Scripts\python.exe" -m mypy backend/src

# Tests
& ".\.venv\Scripts\python.exe" -m pytest backend/tests -v

# Coverage
& ".\.venv\Scripts\python.exe" -m pytest backend/tests -v --cov=backend/src --cov-report=term-missing --cov-report=html
```

Artifacts:

- Coverage XML: coverage.xml (root)
- Coverage HTML: htmlcov/index.html

---

## 7) Production checklist (harden before deploy)

Security

- Generate strong SECRET_KEY and ENCRYPTION_KEY (never commit).
- Restrict or disable docs in production (FastAPI docs_url/redoc_url) if needed.
- Ensure no secrets in repo (run a secret scan; fix any findings).

Observability

- Prometheus and Grafana enabled; verify scrape targets and dashboards.
- Decide log shipping strategy (structured logs are enabled).

Performance

- Confirm Ollama model choices fit your hardware and latency targets.
- Tune Redis persistence if needed.

Networking

- Expose only necessary ports; consider a reverse proxy (nginx/traefik) with TLS.

Backups/data

- Back up Docker volumes: redis_data, backend_state, backend_logs, ollama_models.

---

## 8) Deploy the backend

A) Docker Compose (recommended)

```powershell
# On the host
docker compose pull
docker compose up -d

# Verify
curl http://127.0.0.1:8001/health
```

B) Windows service (bare-metal alternative)

- Create a Python venv and install requirements on the server.
- Register FastAPI via a service wrapper (e.g., NSSM):
  - Executable: path\to\.venv\Scripts\python.exe
  - Arguments: -m uvicorn src.main:app --host 0.0.0.0 --port 8001
  - Working directory: backend/
- Ensure Redis and Ollama run as services or via Docker.

---

## 9) Package and publish the VS Code extension

Prepare metadata: `extension/package.json` should have the correct `publisher`, `version`, and README/icon.

Build and package:

```powershell
cd extension
npm ci
npm run package   # emits .vsix
```

Publish to Marketplace:

```powershell
# One-time publisher setup in Marketplace portal
# Then create a PAT with Publish scope

setx VSCE_PAT "<your_token>"
npm run package:publish
```

Optional release via GitHub:

- Tag the repo (e.g., v1.0.1), create a release, and attach the .vsix.

---

## 10) Release process (single checklist)

Pre-release gates

- Lint, Format, Type check, Tests, Coverage → all PASS.
- Update CHANGELOG and bump versions (backend and extension) using semver.
- Optional: run secret scans and dependency audits.

Tag and build

- Tag: vX.Y.Z
- Build .vsix (extension) and, if desired, build/push backend images.

Publish

- Publish extension to Marketplace (or attach .vsix to the GitHub release).
- Deploy backend (Compose or service), verify health and dashboards.

Announce

- Link to README.md, DEPLOYMENT_GUIDE.md, EXTENSION_DEVELOPMENT.md.
- Note supported OS, prerequisites, model recommendations.

---

## 11) Troubleshooting quick hits

- “pip not recognized” in tasks: ensure tasks call `${workspaceFolder}/.venv/Scripts/python.exe` -m ... (already done).
- Tests skipping Ollama: start the Ollama service or run via Docker Compose to enable integration tests.
- Extension can’t connect: verify backend on <http://127.0.0.1:8001> and ws://127.0.0.1:8001/ws, and match settings.
- Ports in use: adjust in docker-compose.yml and VS Code tasks consistently.

---

## 12) Optional small alignments

- Black line length is 100 in tasks; editor settings may be 88. Pick one and unify.
- Add a VS Code debug launch for breakpoints against the FastAPI app if desired.

---

That’s it. Follow sections 2–6 to get to a working local baseline, 7–8 to harden and deploy the backend, and 9–10 to publish the extension.
