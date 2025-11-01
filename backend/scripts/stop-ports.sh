#!/usr/bin/env bash
set -euo pipefail

# Stop uvicorn processes started via start-agent.sh by port, or best-effort kill by port
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

ports=("$@")
if [[ ${#ports[@]} -eq 0 ]]; then ports=(8001 8002 8003); fi

for p in "${ports[@]}"; do
  pidfile="pids/uvicorn-${p}.pid"
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile" || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
      echo "Stopped pid $pid for port $p"
    fi
    rm -f "$pidfile"
  else
    if command -v fuser >/dev/null 2>&1; then
      fuser -k "${p}/tcp" || true
    elif command -v lsof >/dev/null 2>&1; then
      lsof -ti tcp:"$p" | xargs -r kill || true
    fi
  fi
 done
