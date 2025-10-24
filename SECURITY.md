# Security Guidelines

This project is configured for local-first development with production hardening options.

## Secrets
- Do not commit real secrets. The file `backend/.env.production` is ignored by git.
- Use the top-level `.env` for non-sensitive compose variables. A safe template is provided as `.env.example`.
- For production, store secrets in a managed secret store (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager) and inject at runtime.

## TLS and Reverse Proxy
- Caddy terminates TLS and routes `/api`, `/grafana`, and `/prometheus`.
- Set `SERVER_DOMAIN` and `ACME_EMAIL` for ACME issuance and renewal.
- Access logs are enabled and rotated by default; stored in the `caddy_logs` volume.

## Observability and Alerts
- Prometheus scrapes backend, celery worker, caddy, ollama, and itself.
- Alert rules are in `monitoring/alerts.yml`. Tune thresholds to your SLOs.
- Grafana alerting is provisioned. Set `GRAFANA_ALERT_WEBHOOK_URL` to receive alerts.

## Network Exposure
- Use `docker-compose.prod.yml` to avoid exposing internal ports. Only Caddy (80/443) should be public in production.

## Dependency and CI
- CI runs linting, tests, builds Docker images and packages the extension.
- Release workflow tags build and publish artifacts.

## Incident Response
- Keep rotation and incident playbooks up to date in the repo docs.
- Ensure log retention for Caddy and application logs as per your compliance requirements.
