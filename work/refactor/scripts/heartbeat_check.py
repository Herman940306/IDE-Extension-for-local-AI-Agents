#!/usr/bin/env python3
"""
Weekly heartbeat check script.
- Probes a BASE_URL for:
  - /api/health
  - /grafana/api/health
  - /prometheus/-/ready
- Supports INSECURE TLS via env HEARTBEAT_INSECURE=true
- Exits 0 on success, non-zero on any failure.
"""

import json
import os
import ssl
import sys
import time
from urllib import error, request

BASE_URL = os.getenv("HEARTBEAT_BASE_URL", "").strip()
INSECURE = os.getenv("HEARTBEAT_INSECURE", "false").lower() in {"1", "true", "yes"}
TIMEOUT = float(os.getenv("HEARTBEAT_TIMEOUT", "10"))
RETRIES = int(os.getenv("HEARTBEAT_RETRIES", "3"))
SLEEP = float(os.getenv("HEARTBEAT_RETRY_SLEEP", "3"))

if not BASE_URL or BASE_URL.lower() == "disabled":
    print("Heartbeat disabled: HEARTBEAT_BASE_URL not set or disabled.")
    sys.exit(0)

BASE_URL = BASE_URL.rstrip("/")
ctx = None
if INSECURE:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

checks = [
    {
        "name": "api_health",
        "path": "/api/health",
        "validator": lambda code, body: (
            code == 200 and ("ok" in body.lower() or '"ok"' in body.lower())
        ),
    },
    {
        "name": "grafana_health",
        "path": "/grafana/api/health",
        "validator": lambda code, body: (
            code == 200 and ("ok" in body.lower() or "database" in body.lower())
        ),
    },
    {
        "name": "prom_ready",
        "path": "/prometheus/-/ready",
        "validator": lambda code, body: (
            code == 200 and "prometheus server is ready" in body.lower()
        ),
    },
]

results = []

for chk in checks:
    url = BASE_URL + chk["path"]
    success = False
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = request.Request(url, method="GET")
            with request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
                code = resp.getcode()
                body = resp.read().decode("utf-8", errors="replace")
                ok = chk["validator"](code, body)
                if ok:
                    success = True
                    results.append(
                        {
                            "check": chk["name"],
                            "url": url,
                            "status": "ok",
                            "code": code,
                        }
                    )
                    break
                else:
                    last_err = f"Unexpected response (code={code})"
        except error.HTTPError as e:
            last_err = f"HTTPError {e.code}: {e.reason}"
        except error.URLError as e:
            last_err = f"URLError: {e.reason}"
        except Exception as e:
            last_err = f"Exception: {e}"
        if attempt < RETRIES:
            time.sleep(SLEEP)
    if not success:
        results.append(
            {
                "check": chk["name"],
                "url": url,
                "status": "fail",
                "error": last_err,
            }
        )

failed = [r for r in results if r["status"] != "ok"]
print("Heartbeat summary:")
print(json.dumps(results, indent=2))

if failed:
    print("One or more checks failed.")
    sys.exit(1)
else:
    print("All checks passed.")
    sys.exit(0)
