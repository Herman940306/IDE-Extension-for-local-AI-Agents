#!/usr/bin/env python3
# Core router logic (simplified runtime-ready)
import logging
import subprocess
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
ROUTING_YAML = Path("AuralA_Model_Routing_Generated.yaml")


def load_routing():
    if ROUTING_YAML.exists():
        return yaml.safe_load(ROUTING_YAML)
    return {"model_assignments": {}}


def route_request_stub(task_type, prompt, context=None):
    # Minimal stub that calls ollama models based on YAML mapping
    cfg = load_routing().get("model_assignments", {})
    primary = cfg.get("system_1_fast_reasoner")
    if isinstance(primary, dict):
        primary = primary.get("model")
    if not primary:
        primary = cfg.get("system_1_fast_reasoner", "llama3.2:3b")
    cmd = ["ollama", "run", primary, "--stdin"]
    p = subprocess.run(
        cmd,
        input=prompt.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    text = p.stdout.decode(errors="ignore").strip()
    return {"text": text, "model": primary, "latency": None}


# expose small API for import
def route_request(task_type, prompt, context=None):
    return route_request_stub(task_type, prompt, context)


if __name__ == "__main__":
    print("router.py standalone test. Loading routing...")
    print(load_routing())
