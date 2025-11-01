#!/usr/bin/env bash
set -euo pipefail

# Start three agents on ports 8001/8002/8003 with APP_INSTANCE agent-1/2/3
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/start-agent.sh" 8001 agent-1
sleep 2
"$SCRIPT_DIR/start-agent.sh" 8002 agent-2
sleep 2
"$SCRIPT_DIR/start-agent.sh" 8003 agent-3

# Poll /docs for readiness
for p in 8001 8002 8003; do
  echo "Waiting for http://127.0.0.1:${p}/docs ..."
  for i in {1..30}; do
    if curl -fsS "http://127.0.0.1:${p}/docs" >/dev/null; then
      echo "Agent on ${p} is up"
      break
    fi
    sleep 1
  done
done
