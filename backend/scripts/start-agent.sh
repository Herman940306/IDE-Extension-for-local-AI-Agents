#!/usr/bin/env bash
set -euo pipefail

# Start a single FastAPI agent with Uvicorn on the given port.
# Usage: ./start-agent.sh [port] [app_instance]
# Defaults: port=8001, app_instance=agent-1

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$DIR"

PORT="${1:-8001}"
APP_INSTANCE="${2:-agent-1}"

# Choose Python
if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x ".venv/bin/python" ]]; then PYTHON=".venv/bin/python"; else PYTHON="python3"; fi
fi

mkdir -p logs pids
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export APP_INSTANCE="$APP_INSTANCE"
export PYTHONPATH="$DIR"

nohup "$PYTHON" -m uvicorn src.main:app \
  --host 127.0.0.1 \
  --port "$PORT" \
  --log-level info \
  > "logs/agent-${PORT}.log" 2>&1 &
PID=$!
echo $PID > "pids/uvicorn-${PORT}.pid"
echo "Started APP_INSTANCE=$APP_INSTANCE on port $PORT (pid=$PID)"
