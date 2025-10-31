#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

REQS = ["fastapi", "uvicorn[standard]", "pyyaml", "psutil", "requests", "GPUtil"]
print("Starting AuralA setup...")
# install deps
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + REQS)
except Exception as e:
    print("Warning: pip install may have failed. Ensure dependencies are installed:", e)


# detect callback port
def find_callback():
    for p in range(3000, 3011):
        try:
            import requests

            url = f"http://localhost:{p}/notify"
            resp = requests.options(url, timeout=0.6)
            if resp.status_code in (200, 204, 404, 405):
                return url
        except Exception:
            continue
    return "http://localhost:3000/notify"


cfg = {"callback_url": find_callback(), "port": 5050}
Path("config.json").write_text(json.dumps(cfg, indent=2))
print("Config written to config.json:", cfg)
print("Launching router_http.py ...")
# launch server
try:
    subprocess.check_call([sys.executable, "router_http.py"])
except Exception as e:
    print("Failed to launch router_http.py:", e)
    print("You can run it manually: python router_http.py")
