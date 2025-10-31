#!/usr/bin/env python3
import json
import logging
import threading
import time
from pathlib import Path

import requests
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request
from pydantic import BaseModel
from router import route_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
APP = FastAPI()
CONFIG = Path("config.json")
METRICS_FILE = Path("aura_metrics.json")
ROUTING_YAML = Path("AuralA_Model_Routing_Generated.yaml")

# load or create config
if not CONFIG.exists():
    CONFIG.write_text(
        json.dumps({"callback_url": "http://localhost:3000/notify", "port": 5050}, indent=2)
    )
with open(CONFIG) as f:
    cfg = json.load(f)

# simple in-memory metrics
metrics = {}
metrics_lock = threading.Lock()


def persist_metrics():
    with metrics_lock:
        METRICS_FILE.write_text(json.dumps(metrics, indent=2))


def send_notification(payload):
    try:
        url = cfg.get("callback_url")
        if not url:
            return
        requests.post(url, json=payload, timeout=2)
    except Exception as e:
        logging.debug("Callback failed: %s", e)


class RouteReq(BaseModel):
    task_type: str
    prompt: str
    context: str = None


@APP.post("/route")
async def route_endpoint(req: RouteReq, background_tasks: BackgroundTasks):
    start = time.time()
    result = route_request(req.task_type, req.prompt, req.context)
    latency = time.time() - start
    model = result.get("model", "unknown")
    # update metrics
    with metrics_lock:
        m = metrics.get(model, {"calls": 0, "avg_latency": 0.0, "success": 0})
        calls = m["calls"] + 1
        avg = (m["avg_latency"] * m["calls"] + latency) / calls if m["calls"] > 0 else latency
        succ = m["success"] + (1 if result.get("text") else 0)
        metrics[model] = {"calls": calls, "avg_latency": avg, "success": succ}
        persist_metrics()
    # check if autotune suggestion (simple threshold)
    if metrics[model]["avg_latency"] > 5.0:
        payload = {
            "message": "Model " + model + " showing high latency",
            "model": model,
            "avg_latency": metrics[model]["avg_latency"],
        }
        background_tasks.add_task(send_notification, payload)
    return {
        "text": result.get("text"),
        "verified": result.get("verified", False),
        "metadata": {"model": model, "latency": latency},
    }


@APP.get("/metrics")
async def get_metrics():
    return metrics


@APP.post("/autotune")
async def autotune_endpoint(body: dict):
    # body expected: {"approve": True}
    approve = body.get("approve", False)
    if approve:
        # here we would write to YAML - simplified: just echo
        return {
            "status": "accepted",
            "note": "In a real deployment this would rewrite routing YAML per metrics",
        }
    return {"status": "rejected"}


@APP.post("/notify")
async def notify_endpoint(req: Request):
    j = await req.json()
    logging.info("Received notify: %s", j)
    return {"ok": True}


if __name__ == "__main__":
    port = cfg.get("port", 5050)
    logging.info("Starting AuralA HTTP Router on port %s", port)
    uvicorn.run(APP, host="0.0.0.0", port=port)
