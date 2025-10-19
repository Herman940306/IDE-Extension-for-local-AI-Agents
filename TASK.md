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
- [ ] **Extension Packaging**: Produce signed VSIX, validate version bump, and document install steps in `README.md` release section.
- [ ] **Accessibility Pass**: Confirm extension UI meets WCAG AA; document results in `ACCESSIBILITY_IMPLEMENTATION.md`.
- [ ] **Telemetry Controls**: Expose toggle in extension settings for analytics collection; ensure default respects privacy-first stance.

## Phase 4 – Infrastructure & Deployment Automation

- [ ] **Production Env Provisioning**: Complete TODO block in `PRODUCTION_DEPLOYMENT_GUIDE.md` (env file, secure keys, Redis/Ollama endpoints, monitoring).
- [ ] **Docker Images Hardening**: Review `backend/Dockerfile` for multi-stage build, non-root execution, dependency pinning; publish to container registry.
- [ ] **Compose & IaC Updates**: Extend `docker-compose.yml` with production-ready services (Redis, Ollama proxy, monitoring stack); consider Terraform/Bicep equivalents.
- [ ] **CI/CD Pipeline**: Implement branch protection + PR checks (lint, tests, build, package); add deployment job triggered on `main` tag.
- [ ] **Disaster Recovery**: Document backup/restore procedure for Redis and ChromaDB in `SYSTEM_RECOVERY.md`.

## Phase 5 – Security, Compliance & Documentation

- [ ] **Threat Modelling Review**: Conduct STRIDE session; capture findings in `SECURITY_THREAT_MODEL.md` (new file) with mitigations.
- [ ] **Secret Scanning & DLP**: Configure repo secret scanners (GitHub Advanced Security or gitleaks) and add runbook in `MONITORING_GUIDE.md`.
- [ ] **Privacy Impact Assessment**: Ensure cloud fallback sanitisation documented; append data flow diagram to `PRIVACY_COMPLIANCE.md` (new).
- [ ] **User Onboarding Materials**: Update `QUICK_START.md` and `PROJECT_SETUP.md` with latest install/run/verify steps.
- [ ] **Final Deployment Simulation**: Execute dry-run deployment to staging, run smoke tests, and record outcomes in `DEPLOYMENT_READY_SUMMARY.md`.

---

## Cross-Cutting Tasks

- [ ] **Branch Hygiene**: Enforce `feature/*` workflow; auto-delete merged branches; document in `.kiro/steering/git-workflow.md` appendix.
- [ ] **Metrics Instrumentation**: Implement Prometheus exporters or equivalent; wire dashboards referenced in `MONITORING_GUIDE.md`.
- [ ] **Change Log Maintenance**: Resume release notes in `PROJECT_SUMMARY.md`; include highlights per phase completion.
- [ ] **Stakeholder Reviews**: Schedule fortnightly checkpoints with product/QA/security; log decisions in `SPRINT_PROGRESS_UPDATE.md`.

---

## Completion Definition

A phase is considered DONE when all tasks are checked, automated tests (unit + integration) pass on CI, documentation is updated, and stakeholders sign off. Track progress by mirroring checkbox states in `IMPLEMENTATION_PROGRESS.md` or your preferred project tracker.
