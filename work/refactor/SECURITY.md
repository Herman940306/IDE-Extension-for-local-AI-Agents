# Security Policy

**AuraIA** takes security seriously. This document outlines our security practices, supported versions, and how to report vulnerabilities.

---

## 🛡️ Supported Versions

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 1.0.0-alpha | ✅ Yes | Active Development |
| < 1.0.0 | ❌ No | Prototype/Archived |

We provide security updates for the latest alpha release. Once we reach stable (1.0.0+), we'll support the current major version and one previous version.

---

## 🔒 Reporting a Vulnerability

**Please DO NOT report security vulnerabilities through public GitHub issues.**

### Preferred Method: Private Security Advisory

1. Go to our [Security Advisories page](https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents/security/advisories)
2. Click "Report a vulnerability"
3. Fill in the details using the template below

### Alternative: Email

If you prefer email, send your report to: **herman940306@gmail.com**
- Use subject line: `[SECURITY] AuraIA Vulnerability Report`
- Encrypt sensitive information using our PGP key (if available)

### What to Include

```
**Title:** Brief description of the vulnerability

**Severity:** Critical / High / Medium / Low

**Component:** Backend API / Frontend UI / Extension / LLM Integration / Other

**Description:**
[Detailed description of the vulnerability]

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. ...

**Impact:**
[What can an attacker do? What data is at risk?]

**Suggested Fix:**
[Optional - your ideas for fixing the issue]

**Proof of Concept:**
[Code, screenshots, or logs demonstrating the issue]
```

### Response Timeline

- **24 hours:** Initial acknowledgment
- **72 hours:** Preliminary assessment and severity rating
- **7 days:** Detailed response with remediation plan
- **30 days:** Fix released (for critical/high severity)

### Disclosure Policy

- We follow **coordinated disclosure**
- We'll work with you to understand and fix the issue
- Public disclosure after patch is released (typically 90 days)
- Security advisories published on GitHub
- Credit given to reporters (unless you prefer anonymity)

---

## 🔐 Security Best Practices

This project is configured for local-first development with production hardening options.

### 🔑 Secrets Management

- Do not commit real secrets. The file `backend/.env.production` is ignored by git.
- Use the top-level `.env` for non-sensitive compose variables. A safe template is provided as `.env.example`.
- For production, store secrets in a managed secret store (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager) and inject at runtime.
- **Never commit:**
  - API keys (OpenAI, Anthropic, etc.)
  - Database passwords
  - JWT secrets
  - Private keys
  - OAuth client secrets

### 🌐 Network Security

- Use `docker-compose.prod.yml` to avoid exposing internal ports. Only Caddy (80/443) should be public in production.
- **Development:** Backend on `127.0.0.1:8001`, Frontend on `127.0.0.1:3000`
- **Production:** All services behind reverse proxy (Caddy)
- Enable CORS only for trusted origins
- Use rate limiting to prevent abuse

### 🔐 TLS and Encryption

- Caddy terminates TLS and routes `/api`, `/grafana`, and `/prometheus`.
- Set `SERVER_DOMAIN` and `ACME_EMAIL` for ACME issuance and renewal.
- Access logs are enabled and rotated by default; stored in the `caddy_logs` volume.
- **Minimum TLS version:** 1.2 (recommend 1.3)
- **Cipher suites:** Modern, forward-secret ciphers only
- **HSTS:** Enabled with `max-age=31536000; includeSubDomains`

### 📊 Monitoring and Alerting

- Prometheus scrapes backend, celery worker, caddy, ollama, and itself.
- Alert rules are in `monitoring/alerts.yml`. Tune thresholds to your SLOs.
- Grafana alerting is provisioned. Set `GRAFANA_ALERT_WEBHOOK_URL` to receive alerts.
- **Monitor for:**
  - Unusual API request patterns
  - Failed authentication attempts
  - High error rates
  - Resource exhaustion
  - Unauthorized access attempts

### 🔧 Dependency Management

- CI runs linting, tests, builds Docker images and packages the extension.
- Release workflow tags build and publish artifacts.
- **Keep dependencies updated:**
  - Run `pip-audit` for Python vulnerabilities
  - Run `npm audit` for JavaScript vulnerabilities
  - Review Dependabot alerts weekly
  - Update critical vulnerabilities within 48 hours

### 🚨 Incident Response

- Keep rotation and incident playbooks up to date in the repo docs.
- Ensure log retention for Caddy and application logs as per your compliance requirements.
- **Response Plan:**
  1. **Detect:** Monitor logs and alerts
  2. **Assess:** Determine severity and impact
  3. **Contain:** Isolate affected systems
  4. **Remediate:** Apply patches/fixes
  5. **Communicate:** Notify affected users
  6. **Review:** Post-mortem and lessons learned

---

## 🎯 Security Features in AuraIA

### Local-First Privacy
- **LLM runs locally** via Ollama (no cloud transmission by default)
- **Code stays on your machine** unless you explicitly enable cloud models
- **No telemetry** in open-source version

### Input Validation
- All user inputs sanitized and validated
- SQL injection prevention (parameterized queries)
- XSS prevention (escaped output)
- Path traversal protection

### Authentication & Authorization
- WebSocket connection authentication (when enabled)
- API endpoint authorization
- Rate limiting per user/IP
- Token expiration and rotation

### Code Safety
- Safety layer validates generated code
- PII detection before LLM transmission
- Dangerous operation warnings
- Sandbox execution for code verification

---

## 🏆 Security Hall of Fame

We recognize researchers who help improve AuraIA's security:

*No reports yet - be the first!*

Thank you to all security researchers who responsibly disclose vulnerabilities.

---

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)

---

**Questions?** Contact: herman940306@gmail.com
**Project:** [AuraIA - IDE-Extension-for-local-AI-Agents](https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents)
