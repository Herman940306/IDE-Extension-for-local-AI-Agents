# Release Notes

## v1.0.0

Highlights
- Local-first AI assistant for VS Code with dual-process reasoning (System 1 + System 2)
- Fully local LLMs via Ollama (llama3.2:3b for fast reasoning, mistral:7b for analytical verification)
- Clean HTTPS routes via Caddy: /api, /grafana, /prometheus
- Observability out of the box (Prometheus + Grafana), email alert smoke test in failure-only mode

What’s included
- VS Code extension (VSIX) for explain/refactor/debug commands with backend orchestration
- FastAPI backend exposing /api/health and /metrics
- Provisioned Grafana datasource, alerting, and dashboards
- Prometheus recording rules (request rates, p90/p99 latency)

How to run (quick)
1) Install Docker Desktop.
2) Copy .env.example to .env and adjust values (SMTP optional).
3) docker compose up -d
4) Health checks via Caddy:
   - https://localhost/api/health
   - https://localhost/grafana/api/health
   - https://localhost/prometheus/-/ready
5) Install the VSIX in VS Code (Extensions view → ellipsis → Install from VSIX):
   - extension/aura-ai-assistant-1.0.0.vsix

Known notes
- Grafana admin credentials are set via environment; rotate with SECRETS_ROTATION.md.
- The smoke alert rule fires only if targets go down (sum(up) == 0); email-only route.
- If Ollama models aren’t installed, the extension’s dual-process features will be limited until models are pulled.
