# Secrets Rotation Guide

This guide covers safe rotation of Grafana admin credentials and related secrets used by the local stack and CI.

## Grafana admin password

Grafana is configured via environment variables in `docker-compose.yml`:

- `GF_SECURITY_ADMIN_USER` (default `admin`)
- `GF_SECURITY_ADMIN_PASSWORD` (default `change_me`)

Recommended rotation procedure:

1) Choose a new strong password.
2) Set it in your local environment (e.g., in a `.env` file or shell export) before starting/restarting the stack:
   - PowerShell: `$Env:GRAFANA_ADMIN_PASSWORD = '...new...'`
   - Bash: `export GRAFANA_ADMIN_PASSWORD='...new...'`
3) Restart Grafana to apply:
   - `docker compose restart grafana`
4) Log in to Grafana using the new credentials.

Notes:
- Compose already references `${GRAFANA_ADMIN_PASSWORD}` and `${GRAFANA_ADMIN_USER}`; avoid committing real secrets.
- For production-like deployments, store secrets in a secure secret manager or CI/CD secrets.

## Email SMTP credentials

If using Gmail App Passwords:

1) Generate a new App Password from your Google account (2FA required).
2) Set the following environment variables before restart:
   - `GF_SMTP_USER`
   - `GF_SMTP_PASSWORD`
   - Optional from-address/name: `GF_SMTP_FROM_ADDRESS`, `GF_SMTP_FROM_NAME`
3) Restart Grafana: `docker compose restart grafana`

## CI configuration (GitHub)

The weekly heartbeat workflow uses repository variables to configure the base URL and TLS mode:

- `HEARTBEAT_BASE_URL`: Public base URL (e.g., `https://example.com`).
- `HEARTBEAT_INSECURE`: `true` to ignore TLS verification (self-signed certs).

Set these under: GitHub → Settings → Variables → Repository variables.

If you later add deployment workflows that need secrets (e.g., `GRAFANA_ADMIN_PASSWORD`), store them under:

- GitHub → Settings → Secrets and variables → Actions → Secrets → `GRAFANA_ADMIN_PASSWORD`

Then reference them in workflow `env` as `${{ secrets.GRAFANA_ADMIN_PASSWORD }}`.

## Verification after rotation

- Grafana login succeeds with new password at `https://localhost/grafana`.
- Alert emails are still delivered (trigger smoke test in Grafana or use the one-click script).
- CI weekly heartbeat continues to pass.

## Incident fallback

If you lose admin access:

- Stop Grafana container and delete the Grafana storage volume to reset credentials (will erase UI-created dashboards):
  - `docker compose down`
  - `docker volume rm <repo>_grafana_data`
  - `docker compose up -d`
- Alternatively, run Grafana with `GF_SECURITY_ADMIN_PASSWORD` set to a known temporary value and rotate immediately after login.
