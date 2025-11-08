import time

from fastapi.testclient import TestClient
from src.main import app as main_app


def test_jobs_long_backgroundtasks_path_completes():
    client = TestClient(main_app)

    # Submit a short job (should use BackgroundTasks by default)
    resp = client.post("/jobs/long", json={"duration_seconds": 1})
    assert resp.status_code == 202
    data = resp.json()
    assert data.get("status") == "queued"
    assert "job_id" in data

    job_id = data["job_id"]

    # Poll for completion
    deadline = time.time() + 5
    final = None
    while time.time() < deadline:
        s = client.get(f"/jobs/status/{job_id}")
        assert s.status_code == 200
        body = s.json()
        if body.get("status") in ("completed", "failed"):
            final = body
            break
        time.sleep(0.2)

    assert final is not None, "job did not complete in time"
    assert final["status"] == "completed"


def test_metrics_endpoint_exposes_prometheus_format():
    client = TestClient(main_app)

    # Hit health to increment HTTP request counters
    _ = client.get("/health")

    # Scrape metrics
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text

    # Basic sanity checks for Prometheus exposition format and known metrics
    assert "# HELP" in text
    assert "http_requests_total" in text
