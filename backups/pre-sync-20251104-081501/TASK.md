# AuraIA Deployment Readiness Task Plan

> Comprehensive backlog of outstanding work required to reach a production-ready, fully deployable release. Tasks are grouped into sequential phases; complete each phase before advancing unless otherwise noted. Status defaults to `TODO`.

---

## Phase 0 – Baseline Validation & Observability

- [x] **Inventory Current State**: Capture committed versions of `backend/requirements*.txt`, `pyproject.toml`, and extension `package.json`; document in `IMPLEMENTATION_PROGRESS.md`.
- [x] **Restore CI Visibility**: Ensure GitHub Actions self-hosted runners are online and green for lint/test workflows; add dashboard link in `MONITORING_GUIDE.md`.
- [x] **Centralise Failure Logs**: Collect latest pytest output and archive in `logs/pytest/2025-10-19.log` for ongoing reference.
- [x] **Set Success Metrics**: Publish current KPIs (coverage 43%, latency targets) in `COMPREHENSIVE_TEST_RESULTS.md`.

## Phase 1 – Automated Test Suite Recovery

- [x] **Diagnose Pytest Failures**: Run `pytest backend/tests -v` inside `.venv` and confirm suite stability (411 passed / 5 skipped for Ollama).
- [x] **Stabilise Fixtures**: Bootstrap `.venv` via `pip install -r backend/requirements.txt`; Redis async fixtures load without import errors.
- [x] **Re-enable Lint/Format Tasks**: `black` and `flake8 backend` both pass in `.venv`; legacy style violations resolved.
- [x] **Add Regression Cases**: Added coverage for CrewAI adapter normalization and meta orchestrator fallbacks in `backend/tests/unit/test_meta_orchestrator_regressions.py`.
- [x] **Report Test Health**: `COMPREHENSIVE_TEST_RESULTS.md` refreshed with latest metrics and success criteria snapshot.

## Phase 2 – Backend Hardening & Configuration

- [x] **Finalize Dependency Injection Container**: Review `backend/src/core/container.py` for completeness; document wiring diagram and ensure all agents register correctly.
- [x] **Secret Management Workflow**: Implement `.env.production` template referencing `SECRET_KEY`, `ENCRYPTION_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`; integrate with Azure Key Vault or equivalent secret store.
- [x] **Service Health Checks**: Confirm `services/cloud_providers.py` and `llm_manager.py` expose health endpoints; add integration tests targeting failure and retry paths.
- [x] **Rate Limiting & CORS**: Verify FastAPI middleware enforces rate limits and locked-down CORS origins per production requirements.
- [x] **Perf Profiling**: Benchmark critical endpoints (`/api/analyze`, `/ws`) with Ollama and cloud fallback; log CPU/memory footprints to `MONITORING_GUIDE.md`.

## Phase 3 – Frontend & Extension Alignment

- [x] **Sync WebSocket Contracts**: Cross-check `frontend/src/services/websocket.ts` with backend event schema; update TypeScript interfaces and ensure runtime validation.
- [x] **UI State Handling**: Audit `frontend/src/App.tsx` for error/loading states when backend offline; implement user-friendly notifications.
- [x] **Extension Packaging**: Produce signed VSIX, validate version bump, and document install steps in `README.md` release section. `aura-ai-assistant-1.0.0.vsix` generated via `vsce package` and installation steps recorded.
- [x] **Accessibility Pass**: Confirm extension UI meets WCAG AA; document results in `ACCESSIBILITY_IMPLEMENTATION.md`. NVDA/JAWS/VoiceOver sessions logged (`logs/accessibility/*`) and reduced-motion validation completed; automated audits remain outstanding.
- [x] **Telemetry Controls**: Expose toggle in extension settings for analytics collection; ensure default respects privacy-first stance. Added `enterpriseAI.privacy.allowTelemetry` setting, `Aura: Toggle Telemetry` command, and documentation updates.

## Phase 4 – Infrastructure & Deployment Automation

- [x] **Production Env Provisioning**: Expanded `PRODUCTION_DEPLOYMENT_GUIDE.md` with Azure Key Vault steps, `.env.production` instructions, and monitoring/LLM provisioning guidance.
- [x] **Docker Images Hardening**: Refactored `backend/Dockerfile` to a multi-stage build with pinned Python base digest, compiled artifacts, and non-root runtime user. Ready for registry publishing.
- [x] **Compose & IaC Updates**: Updated `docker-compose.yml` to include Ollama, Prometheus, Grafana, persistent volumes, and health checks plus new `monitoring/prometheus.yml` configuration.
- [x] **CI/CD Pipeline**: GitHub Actions `CI` workflow now runs backend lint/tests, extension packaging, and Docker validation on PRs; `Release` workflow builds + publishes GHCR images and attaches VSIX artifacts on `main-*` tags with documented branch protection rules.
- [x] **Disaster Recovery**: `SYSTEM_RECOVERY.md` details Redis append-only + snapshot backups, offsite retention, and Chroma volume snapshot/restore procedures with validation checklists.
- [x] **Deployment Target & Monitoring**: Selected Azure Container Apps + managed Redis for production, defined `/health` ingress probes, and enabled Prometheus alert rules in `monitoring/alerts.yml`.

## Phase 5 – Security, Compliance & Documentation

- [x] **Threat Modelling Review**: STRIDE analysis published in `SECURITY_THREAT_MODEL.md` covering extension, backend, and infrastructure mitigations.
- [x] **Secret Scanning & DLP**: Added `.gitleaks.toml`, scheduled `secret-scan.yml` workflow, and documented response playbook in `MONITORING_GUIDE.md`.
- [x] **Privacy Impact Assessment**: `PRIVACY_COMPLIANCE.md` details data inventory, minimisation, retention, and cloud fallback sanitisation with text-based data flow.
- [x] **User Onboarding Materials**: Update `QUICK_START.md` and `PROJECT_SETUP.md` with latest install/run/verify steps.
- [x] **Final Deployment Simulation**: Execute dry-run deployment to staging, run smoke tests, and record outcomes in `DEPLOYMENT_READY_SUMMARY.md`.

---

## Cross-Cutting Tasks

- [ ] **Branch Hygiene**: Enforce `feature/*` workflow; auto-delete merged branches; document in `.kiro/steering/git-workflow.md` appendix.
- [ ] **Metrics Instrumentation**: Implement Prometheus exporters or equivalent; wire dashboards referenced in `MONITORING_GUIDE.md`.
- [ ] **Change Log Maintenance**: Resume release notes in `PROJECT_SUMMARY.md`; include highlights per phase completion.
- [ ] **Stakeholder Reviews**: Schedule fortnightly checkpoints with product/QA/security; log decisions in `SPRINT_PROGRESS_UPDATE.md`.

---

## Completion Definition

A phase is considered DONE when all tasks are checked, automated tests (unit + integration) pass on CI, documentation is updated, and stakeholders sign off. Track progress by mirroring checkbox states in `IMPLEMENTATION_PROGRESS.md` or your preferred project tracker.
