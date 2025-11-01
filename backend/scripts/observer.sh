#!/usr/bin/env bash
set -euo pipefail

# Continuously report port status and /docs health for given ports (default 8001 8002 8003)
ports=("$@")
if [[ ${#ports[@]} -eq 0 ]]; then ports=(8001 8002 8003); fi

while true; do
  ts=$(date +"%H:%M:%S")
  for p in "${ports[@]}"; do
    if curl -fsS "http://127.0.0.1:${p}/docs" >/dev/null; then
      status="OK"
    else
      status="DOWN"
    fi
    printf "%s\tport=%s\t/docs=%s\n" "$ts" "$p" "$status"
  done
  sleep 5
done
