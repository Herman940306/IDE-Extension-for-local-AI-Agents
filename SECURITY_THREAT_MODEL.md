# AuraIA Security Threat Model (STRIDE)

**Version:** 1.0  
**Last Updated:** 2025-10-19  
**Prepared By:** Platform Engineering

## 1. Scope

The model covers the AuraIA end-to-end system:
- **VS Code Extension** (TypeScript) interacting with the backend over HTTPS/WebSockets.
- **Backend API** (FastAPI on Azure Container Apps) with Ollama/LLM orchestration.
- **Supporting Services**: Redis cache, Chroma vector store, Ollama runtime, Prometheus/Grafana monitoring, GitHub Actions CI/CD.
- **Data Channels**: user code snippets, telemetry (opt-in), embeddings, secrets managed through Azure Key Vault.

## 2. System Overview

1. Extension sends user prompts or code context to backend over authenticated HTTPS/WebSockets.  
2. Backend orchestrates local Ollama models or cloud LLM fallbacks, persisting embeddings to Chroma and caching sessions in Redis.  
3. Observability supplied via Prometheus/Grafana; CI/CD pipelines publish hardened Docker images and VSIX releases.  
4. Secrets are injected at runtime from Azure Key Vault; persistent data resides on Azure Files volumes.

## 3. Data Classification

| Data Type | Classification | Notes |
|-----------|----------------|-------|
| Source code snippets (generated/analyzed) | Sensitive | User intellectual property; retain only transient copies. |
| Embeddings stored in Chroma | Sensitive | Derived from code; treat as confidential. |
| Telemetry (opt-in) | Internal | Counts/timing only; no code payloads. |
| API keys / secrets | Highly confidential | Managed in Key Vault; never stored in repo or images. |

## 4. STRIDE Analysis

### 4.1 Spoofing

| Asset | Threat | Existing Mitigations | Additional Actions |
|-------|--------|----------------------|--------------------|
| VS Code Extension ↔ Backend | Attacker impersonates backend endpoint | TLS-only communication, certificate pinning via trusted CA, auth token per user session | Implement mutual TLS for enterprise deployments; rotate API keys quarterly. |
| Prometheus targets | Fake metrics endpoint feeding false data | Static service discovery, restricted network security group | Enable Azure Private Link; add basic auth on `/metrics` behind reverse proxy. |

### 4.2 Tampering

| Asset | Threat | Existing Mitigations | Additional Actions |
|-------|--------|----------------------|--------------------|
| In-flight code payloads | MITM alters requests | HTTPS/WSS enforced; HSTS via Application Gateway | Add signing of critical commands or use payload hashing for audit trail. |
| Docker images | Malicious layer injected | Multi-stage Dockerfile pinned to digests; GHCR publishing via Release workflow | Add Cosign signing + verification in CI/CD; enable image scans (Microsoft Defender for Cloud). |

### 4.3 Repudiation

| Asset | Threat | Existing Mitigations | Additional Actions |
|-------|--------|----------------------|--------------------|
| User actions in extension | User denies triggering agent tasks | Structured logging with correlation IDs and user identifiers | Store immutable audit events in Azure Table Storage with retention policy. |
| CI/CD deployments | Untracked production changes | GitHub Actions logs, branch protection rules, release tags | Require signed commits for release branches; archive workflow artifacts to secure storage. |

### 4.4 Information Disclosure

| Asset | Threat | Existing Mitigations | Additional Actions |
|-------|--------|----------------------|--------------------|
| Chroma embeddings | Unauthorized access | Azure Files mount with least-privilege RBAC; container runs as non-root | Encrypt volume at rest using Azure Storage encryption; add application-level encryption before persist. |
| Telemetry data | Leakage of usage metrics | Default telemetry disabled; explicit opt-in setting | Provide data minimization review annually; document retention periods in privacy policy. |
| Secrets in transit | MITM intercepts secrets fetch | Managed identity + Azure Key Vault; HTTPS enforced | Enable Key Vault firewall to VNet only; monitor secret access logs with Sentinel. |

### 4.5 Denial of Service

| Asset | Threat | Existing Mitigations | Additional Actions |
|-------|--------|----------------------|--------------------|
| Backend API | Flooded with requests | Rate limiting middleware; autoscale (min 1 / max 3 replicas) | Add WAF throttling rules; implement circuit breakers for upstream LLM calls. |
| Redis/Ollama | Resource exhaustion | Health probes with restart policies; container resource limits | Configure Azure Monitor alerts on CPU/memory; introduce request queues with back-pressure. |

### 4.6 Elevation of Privilege

| Asset | Threat | Existing Mitigations | Additional Actions |
|-------|--------|----------------------|--------------------|
| Backend container | Breakout to host | Non-root `auraai` user; read-only filesystem except state directories | Enable seccomp/AppArmor profiles; run container in isolated ACA environment per tenant. |
| GitHub Actions runner | Malicious PR executes privileged commands | Branch protection requiring reviews; CI uses hosted runners | Introduce OPA policy checks; move sensitive deployments to reusable workflows with environment approvals. |

## 5. Summary of Recommended Actions

1. Add Cosign signing + verification steps to CI/CD for both backend images and VSIX artifacts.  
2. Restrict Key Vault and storage access via VNet integration and monitor access logs.  
3. Introduce dedicated audit logging storage with retention policies for compliance.  
4. Harden Prometheus/Grafana exposure using Private Link and authentication.  
5. Establish DoS protections at the edge (WAF) and implement circuit breaker patterns for upstream providers.

## 6. Review Cadence

- Revisit the threat model every six months or after major architectural changes.  
- Track remediation of outstanding actions in the security backlog (Phase 5 tasks).
