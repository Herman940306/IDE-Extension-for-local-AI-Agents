<!-- Placeholder: ANTHROPIC_API_KEY not set. Skipping doc rewrite. -->
# AuraIA Phase 5 Deployment Dry-Run Plan

**Owner:** Platform Engineering \
**Last Updated:** 2025-10-19 \
**Status:** Completed (executed 2025-10-19 10:30 UTC)

---

## Objectives

- Validate that the documented production deployment process for AuraIA can be executed end-to-end in a controlled staging environment.
- Exercise the observability, secret management, and rollback procedures defined in `PRODUCTION_DEPLOYMENT_GUIDE.md` and `MONITORING_GUIDE.md`.
- Capture evidence required to update `DEPLOYMENT_READY_SUMMARY.md` and close out Phase 5 item "Final Deployment Simulation" in `TASK.md`.

---

## Environments

| Role        | Target                                                                  | Notes                                                     |
| ----------- | ----------------------------------------------------------------------- | --------------------------------------------------------- |
| Control     | Developer workstation                                                   | Executes `az` CLI, docker, and validation scripts.        |
| Staging     | Azure Container Apps (resource group `rg-auraia-stg`)                   | Mirrors production topology; uses staging secrets.        |
| Monitoring  | Prometheus + Grafana stack                                              | Hosted via docker compose on staging VM `monitor-stg-01`. |
| Data Stores | Azure Cache for Redis (Basic C0), Azure Files share `auraia-chroma-stg` | Provisioned through Terraform stack `infra/staging`.      |

---

## Prerequisites

- Azure subscription with contributor rights to `rg-auraia-stg`.
- `az` CLI authenticated (`az login`) and default subscription set.
- Staging Key Vault `kv-auraia-stg` populated with rotated secrets (`SECRET_KEY`, `ENCRYPTION_KEY`, `DB_REDIS_URL`, `OLLAMA_BASE_URL`, `CHROMA_PERSIST_DIR`).
- Container registry `ghcr.io/herman940306/auraia-backend` populated with the latest image (tag `main-20251019`).
- VSIX package `extension/dist/aura-ai-assistant-1.0.0.vsix` available for compatibility checks.
- Monitoring stack deployed via `docker compose -f monitoring/docker-compose.staging.yml up -d`.

---

## Dry-Run Steps

1. **Artifact Verification**
   - Confirm GHCR image digest matches commit `main@{2025-10-19}` via `az acr repository show-manifests`.
   - Validate VSIX integrity with `vsce verify aura-ai-assistant-1.0.0.vsix`.
2. **Infrastructure Provisioning**
   - Execute `terraform apply -var-file=infra/staging.tfvars` to ensure staging resources are current.
   - Confirm Redis and Azure Files endpoints resolve.
3. **Secret Synchronisation**
   - Run `scripts/sync-secrets.ps1 -Environment staging` to copy secrets into Container Apps environment variables.
   - Trigger gitleaks workflow manually to affirm policy compliance post-rotation.
4. **Container App Deployment**
   - Deploy backend using `az containerapp update --name auraia-backend-stg --image ghcr.io/herman940306/auraia-backend:main-20251019`.
   - Apply revision scaling rules (min 1 / max 3) and confirm `activeRevisionsMode` is `multiple` for rollback.
5. **Extension Compatibility Check**
   - Configure VS Code to point at staging backend URL and run smoke commands (inline suggestion, code action) from the VSIX.
6. **Observability Validation**
   - Verify Prometheus scrape targets show `UP` for backend and Redis.
   - Check Grafana dashboard `AuraIA/Staging` for latency, error rate, and worker saturation metrics.
   - Ensure alert routing triggers the staging Teams channel via test alert.
7. **Functional Smoke Tests**
   - Execute `scripts/smoke_tests.py --env staging` covering `/health`, `/api/analyze`, `/api/agents`.
   - Record response times and confirm SLA (<500ms average).
8. **Rollback Exercise**
   - Swap active revision back to previous image using `az containerapp revision set-mode --revision <prev>` and verify traffic recovery.
   - Restore newest revision post-validation.
9. **Documentation & Sign-off**
   - Collect logs, screenshots, and metrics; archive under `logs/deployment/2025-10-19/`.
   - Update `DEPLOYMENT_READY_SUMMARY.md` and `TASK.md` with outcomes.

---

## Validation Checklist

- [x] GHCR image digest validated.
- [x] Terraform apply completes with no changes pending.
- [x] Container App revision `main-20251019` running and healthy.
- [x] Smoke tests return 2xx responses and meet latency target.
- [x] Alerts propagate to staging channel.
- [x] Rollback revision verified.
- [x] Documentation updated with results.

---

## Roles & Communication

| Role            | Owner                | Responsibilities                                       |
| --------------- | -------------------- | ------------------------------------------------------ |
| Deployment Lead | Platform Engineering | Execute plan, coordinate validation, archive evidence. |
| Security        | SecOps Lead          | Monitor secret handling, approve rollback exercise.    |
| QA              | Quality Guild        | Review smoke test outputs, confirm acceptance.         |
| Observability   | SRE                  | Validate monitoring dashboards and alerts.             |

Communication channel: `#aura-ops` (Teams/Slack bridge). Escalate blockers via incident priority P2.

---

## Exit Criteria

- All checklist items checked.
- Updated documentation contains links to evidence.
- QA sign-off recorded in `MONITORING_GUIDE.md` change log section.
- `TASK.md` Phase 5 "Final Deployment Simulation" marked complete.

---

## Risk & Mitigation

| Risk                                              | Impact | Mitigation                                                     |
| ------------------------------------------------- | ------ | -------------------------------------------------------------- |
| Container App scaling limits throttle smoke tests | Medium | Pre-scale to 3 instances before running tests.                 |
| Secret rotation drifts from production values     | Low    | Use Key Vault backup/restore script `scripts/kv-backup.ps1`.   |
| Alert channel misconfigured                       | Medium | Fire a manual Prometheus alert to confirm.                     |
| Rollback exercise disrupts test metrics           | Low    | Schedule rollback during low-traffic window and document blip. |

---

## Next Review

- After successful dry run, bundle evidence into `DEPLOYMENT_READY_SUMMARY.md` and schedule production go/no-go review for 2025-10-22.
