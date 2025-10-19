# AuraIA Privacy Impact Assessment

**Version:** 1.0  
**Last Updated:** 2025-10-19  
**Prepared By:** Privacy & Compliance Team

## 1. Overview

AuraIA processes developer code snippets and prompts to deliver AI-assisted workflows inside VS Code. This assessment documents data flows, lawful basis, retention policies, and controls to ensure compliance with privacy obligations (GDPR, CCPA, internal corporate policies).

## 2. Data Inventory

| Data Category | Source | Purpose | Storage | Retention |
|---------------|--------|---------|---------|-----------|
| Source code snippets (user provided) | VS Code extension | Generate AI responses | In-memory only | Deleted after request completes |
| AI responses | Backend inference | Provide guidance to user | Returned to client only | Not persisted |
| Embeddings | Backend pipeline | Semantic search & history recall | Chroma volume (`/var/lib/auraia/chroma`) | 30 days (configurable) |
| Session metadata | Redis cache | Conversation continuity | Redis (`appendonly.aof`) | 30 days (auto-expiry) |
| Telemetry (opt-in) | Extension (if enabled) | Measure feature adoption | App Insights / internal logs | 90 days |

## 3. Data Flow Diagram (Text)

1. User triggers an agent command in VS Code.  
2. Extension packages anonymised payload (file path hashed, code snippet truncated if exceeding 2 KB) and sends via HTTPS/WebSocket to backend.  
3. Backend authenticates request, runs inference using local Ollama or cloud provider.  
4. If embeddings required, backend stores vectors in Chroma with `project_id` + `hash(code)` metadata only.  
5. Redis caches session context with expiring keys; keys exclude raw code (hash references only).  
6. Response returned to extension and optionally telemetry counters updated (only feature IDs, no payloads).  
7. Logs capture correlation IDs, timestamps, and anonymised identifiers; no code content stored.

## 4. Lawful Basis & Consent

- **Enterprise deployment:** Legitimate interest to enhance developer productivity.  
- **Telemetry:** Disabled by default; user/admin must explicitly opt-in (`enterpriseAI.privacy.allowTelemetry`).  
- **Cloud fallback (OpenAI/Anthropic):** Requires admin opt-in and contractual DPAs covering sub-processors.

## 5. Data Minimisation Controls

- Client-side truncation of code snippets to minimal context.  
- Hashing of file paths (`sha256`) before transmission.  
- Sanitisation pipeline checks for PII patterns (emails, tokens) and replaces with placeholders before LLM invocation.  
- Embeddings metadata excludes raw filenames/usernames.

## 6. Retention & Deletion

| Data | Policy | Implementation |
|------|--------|----------------|
| Redis session keys | Auto-expire at 30 days | `redis.setex` enforced for session IDs |
| Chroma embeddings | Retain 30 days, purge nightly | Cron job removes vectors older than 30 days by `created_at` metadata |
| Telemetry | 90-day rolling window | Cron job aggregates & purges older logs |
| CI/CD artifacts | 30 days in GitHub Actions | Workflow artifact retention policy enabled |

Users may request deletion via service desk; support triggers manual purge scripts for Chroma and Redis.

## 7. Data Subject Rights

- **Access:** Export conversation history (limited to current session) on request.  
- **Rectification:** Users can correct stored metadata by deleting/restarting session.  
- **Erasure:** Manual purge for embeddings/cache; confirm completion in ticket.  
- **Restriction:** Admin can disable embeddings per tenant via config flag `EMBEDDINGS_ENABLED=false`.

## 8. Third-Party Processors

| Processor | Purpose | Safeguards |
|-----------|---------|------------|
| Azure OpenAI / Anthropic | Cloud inference fallback | DPA on file; requests strip PII and use short-lived tokens |
| Azure Monitor | Telemetry storage | Data encrypted in transit/at rest; limited retention |
| GitHub (Actions, Packages) | CI/CD artifacts | Access restricted to team; PATs rotated quarterly |

## 9. Risk Assessment

| Risk | Impact | Likelihood | Rating | Mitigations |
|------|--------|------------|--------|------------|
| Accidental logging of code | High | Medium | High | Sanitisation filters, structured logging, secure code reviews |
| Cloud provider storing sensitive code | High | Low | Medium | Opt-in only, payload redaction, contractual clauses |
| Unauthorized access to embeddings volume | Medium | Low | Low | Azure Files RBAC, encryption at rest, periodic audits |

## 10. Action Items

1. Implement automated nightly purge job for Chroma embeddings and Redis sessions.  
2. Document data subject request process in service desk knowledge base.  
3. Review telemetry schema quarterly to ensure no inadvertent PII.  
4. Add privacy banner in onboarding materials explaining opt-in controls.

## 11. Review Schedule

- Conduct privacy reassessment every 12 months or before launching new features that introduce additional data capture.
