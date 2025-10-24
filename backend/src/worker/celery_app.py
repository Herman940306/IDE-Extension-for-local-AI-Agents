from __future__ import annotations

import time

from celery import Celery
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from src.core.config import get_settings

settings = get_settings()

# Resolve broker/backend from settings; default to the database Redis URL
broker_url: str = settings.celery_broker_url or settings.database.redis_url
result_backend: str = settings.celery_result_backend or settings.database.redis_url

app = Celery("auraia", broker=broker_url, backend=result_backend)

# Start a lightweight Prometheus metrics server for the worker on port 9100
# This exposes metrics when the worker runs in its own process/container.
try:  # pragma: no cover - side-effect server
    start_http_server(9100)
except Exception:
    # If the port is taken or running locally without need, ignore.
    pass

# Job metrics (worker-side)
WORKER_JOBS_COMPLETED_TOTAL = Counter(
    "jobs_completed_total",
    "Total jobs completed by outcome",
    labelnames=["job_type", "outcome"],
)
WORKER_JOBS_IN_PROGRESS = Gauge(
    "jobs_in_progress", "Current in-progress jobs", labelnames=["job_type"]
)
WORKER_JOB_DURATION_SECONDS = Histogram(
    "job_duration_seconds",
    "Duration of background jobs in seconds",
    labelnames=["job_type", "outcome"],
    buckets=(0.5, 1, 2, 5, 10, 20, 60),
)


@app.task(bind=True, name="auraia.long_job")
def long_job_task(self, duration: float = 5.0, job_type: str = "long") -> dict:
    """Simulated long-running task for Celery workers.

    Returns a small info payload for status endpoints.
    """
    WORKER_JOBS_IN_PROGRESS.labels(job_type=job_type).inc()
    start = time.perf_counter()
    try:
        time.sleep(max(0.0, float(duration)))
        elapsed = time.perf_counter() - start
        WORKER_JOBS_COMPLETED_TOTAL.labels(job_type=job_type, outcome="success").inc()
        WORKER_JOB_DURATION_SECONDS.labels(
            job_type=job_type, outcome="success"
        ).observe(elapsed)
        return {"status": "completed", "duration": elapsed, "job_type": job_type}
    except Exception as e:  # pragma: no cover - defensive
        elapsed = time.perf_counter() - start
        WORKER_JOBS_COMPLETED_TOTAL.labels(job_type=job_type, outcome="error").inc()
        WORKER_JOB_DURATION_SECONDS.labels(job_type=job_type, outcome="error").observe(
            elapsed
        )
        return {
            "status": "failed",
            "error": str(e),
            "duration": elapsed,
            "job_type": job_type,
        }
    finally:
        WORKER_JOBS_IN_PROGRESS.labels(job_type=job_type).dec()
