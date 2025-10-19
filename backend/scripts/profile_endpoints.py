"""Performance profiling utility for AuraIA endpoints.

Measures HTTP and WebSocket latency while optionally sampling backend CPU/memory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import httpx

try:  # psutil is optional at runtime but recommended
    import psutil
except ImportError:  # pragma: no cover - soft dependency
    psutil = None  # type: ignore

try:
    import websockets
except ImportError:  # pragma: no cover - ensures script still runs for HTTP profiling
    websockets = None  # type: ignore

DEFAULT_BASE_URL = "http://127.0.0.1:8001"
DEFAULT_ANALYZE_PATH = "/api/analyze"
DEFAULT_WS_PATH = "/ws/profiler"
DEFAULT_ITERATIONS = 3
DEFAULT_TIMEOUT = 30.0
PROFILE_DIR = Path(__file__).resolve().parents[1] / "logs" / "profiles"


@dataclass
class LatencySummary:
    count: int
    average_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ordered[int(k)]
    return ordered[f] * (c - k) + ordered[c] * (k - f)


def summarise_latencies(latencies: List[float]) -> LatencySummary:
    if not latencies:
        return LatencySummary(count=0, average_ms=0.0, p95_ms=0.0, min_ms=0.0, max_ms=0.0)

    ordered = sorted(latencies)
    average_ms = sum(ordered) / len(ordered)
    return LatencySummary(
        count=len(ordered),
        average_ms=average_ms * 1000.0,
        p95_ms=percentile(ordered, 95.0) * 1000.0,
        min_ms=ordered[0] * 1000.0,
        max_ms=ordered[-1] * 1000.0,
    )


def make_ws_url(base_url: str, path: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc
    if not path.startswith("/"):
        path = f"/{path}"
    return urlunparse((scheme, netloc, path, "", "", ""))


def get_process(pid: Optional[int]):
    if pid is None or psutil is None:
        return None
    try:
        return psutil.Process(pid)
    except Exception:  # pragma: no cover - depends on host OS
        return None


def capture_snapshot(process: Optional[psutil.Process]) -> Optional[Dict[str, float]]:
    if process is None:
        return None
    with process.oneshot():
        cpu_times = process.cpu_times()
        cpu_total = float(cpu_times.user + cpu_times.system)
        memory_mb = float(process.memory_info().rss) / (1024 * 1024)
        return {"cpu_time": cpu_total, "rss_mb": memory_mb}


def compute_resource_usage(
    before: Optional[Dict[str, float]],
    after: Optional[Dict[str, float]],
    elapsed: float,
) -> Optional[Dict[str, float]]:
    if before is None or after is None or elapsed <= 0:
        return None

    cpu_delta = max(0.0, after["cpu_time"] - before["cpu_time"])
    cpu_count = psutil.cpu_count(logical=True) if psutil else None
    cpu_percent = (cpu_delta / elapsed) * 100.0 / cpu_count if cpu_count and cpu_count > 0 else 0.0

    return {
        "cpu_percent": round(cpu_percent, 2),
        "cpu_time_delta": round(cpu_delta, 3),
        "rss_mb_before": round(before["rss_mb"], 2),
        "rss_mb_after": round(after["rss_mb"], 2),
    }


async def profile_http_endpoint(
    base_url: str,
    path: str,
    payload: Dict[str, Any],
    iterations: int,
    timeout: float,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    latencies: List[float] = []
    status_codes: Dict[str, int] = {}
    errors: List[str] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                response = await client.post(url, json=payload)
                latency = time.perf_counter() - start
                latencies.append(latency)
                key = str(response.status_code)
                status_codes[key] = status_codes.get(key, 0) + 1
            except Exception as exc:  # pragma: no cover - network dependent
                errors.append(str(exc))

    summary = summarise_latencies(latencies)
    return {
        "url": url,
        "latencies_ms": {
            "average": round(summary.average_ms, 2),
            "p95": round(summary.p95_ms, 2),
            "min": round(summary.min_ms, 2),
            "max": round(summary.max_ms, 2),
            "samples": summary.count,
        },
        "status_counts": status_codes,
        "errors": errors,
    }


async def profile_websocket_endpoint(
    base_url: str,
    path: str,
    iterations: int,
    timeout: float,
) -> Dict[str, Any]:
    if websockets is None:
        return {"url": path, "error": "websockets package not available"}

    uri = make_ws_url(base_url, path)
    handshake_latencies: List[float] = []
    round_trip_latencies: List[float] = []
    errors: List[str] = []

    for _ in range(iterations):
        try:
            start = time.perf_counter()
            async with websockets.connect(uri, ping_interval=None) as ws:
                handshake_latencies.append(time.perf_counter() - start)

                # Drain welcome message from server before sending ping
                try:
                    await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    errors.append("welcome message timeout")
                    continue

                ping_payload = json.dumps({"type": "ping"})
                round_start = time.perf_counter()
                await ws.send(ping_payload)
                await asyncio.wait_for(ws.recv(), timeout=timeout)
                round_trip_latencies.append(time.perf_counter() - round_start)
        except Exception as exc:  # pragma: no cover - network dependent
            errors.append(str(exc))

    handshake_summary = summarise_latencies(handshake_latencies)
    round_trip_summary = summarise_latencies(round_trip_latencies)

    return {
        "url": uri,
        "handshake_ms": {
            "average": round(handshake_summary.average_ms, 2),
            "p95": round(handshake_summary.p95_ms, 2),
            "min": round(handshake_summary.min_ms, 2),
            "max": round(handshake_summary.max_ms, 2),
            "samples": handshake_summary.count,
        },
        "round_trip_ms": {
            "average": round(round_trip_summary.average_ms, 2),
            "p95": round(round_trip_summary.p95_ms, 2),
            "min": round(round_trip_summary.min_ms, 2),
            "max": round(round_trip_summary.max_ms, 2),
            "samples": round_trip_summary.count,
        },
        "errors": errors,
    }


async def run_profiling(args: argparse.Namespace) -> Dict[str, Any]:
    process = get_process(args.pid)
    if process is not None and psutil is not None:
        process.cpu_percent(interval=None)  # prime internal counters

    http_before = capture_snapshot(process)
    http_start = time.perf_counter()
    http_result = await profile_http_endpoint(
        base_url=args.base_url,
        path=args.analyze_path,
        payload=args.payload,
        iterations=args.iterations,
        timeout=args.timeout,
    )
    http_elapsed = time.perf_counter() - http_start
    http_after = capture_snapshot(process)
    http_resources = compute_resource_usage(http_before, http_after, http_elapsed)

    ws_before = capture_snapshot(process)
    ws_start = time.perf_counter()
    ws_result = await profile_websocket_endpoint(
        base_url=args.base_url,
        path=args.ws_path,
        iterations=args.iterations,
        timeout=args.timeout,
    )
    ws_elapsed = time.perf_counter() - ws_start
    ws_after = capture_snapshot(process)
    ws_resources = compute_resource_usage(ws_before, ws_after, ws_elapsed)

    timestamp = datetime.utcnow().isoformat() + "Z"

    return {
        "timestamp": timestamp,
        "base_url": args.base_url,
        "iterations": args.iterations,
        "http": {
            **http_result,
            "elapsed_seconds": round(http_elapsed, 3),
            "resources": http_resources,
        },
        "websocket": {
            **ws_result,
            "elapsed_seconds": round(ws_elapsed, 3),
            "resources": ws_resources,
        },
        "pid": args.pid,
    }


def parse_payload(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {
            "task_type": "analysis",
            "description": "Profiling latency for core endpoint",
            "code_context": "print('hello world')",
            "language": "python",
            "code": "print('hello world')",
            "provider": "ollama",
        }
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Profile AuraIA endpoints")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend base URL")
    parser.add_argument(
        "--analyze-path",
        default=DEFAULT_ANALYZE_PATH,
        help="HTTP endpoint path to profile (default: /api/analyze)",
    )
    parser.add_argument(
        "--ws-path",
        default=DEFAULT_WS_PATH,
        help="WebSocket endpoint path to profile (default: /ws/profiler)",
    )
    parser.add_argument(
        "--iterations", type=int, default=DEFAULT_ITERATIONS, help="Number of samples per endpoint"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--payload",
        help="JSON payload for analyze endpoint (defaults to sample code request)",
    )
    parser.add_argument(
        "--pid",
        type=int,
        help="Backend process ID for CPU/memory sampling (optional)",
    )
    parser.add_argument(
        "--output",
        help="Optional output file path. Defaults to backend/logs/profiles/<timestamp>.json",
    )
    return parser


def ensure_output_path(custom_path: Optional[str]) -> Path:
    if custom_path:
        path = Path(custom_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"profile-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    return PROFILE_DIR / filename


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    args.payload = parse_payload(args.payload)

    results = asyncio.run(run_profiling(args))

    output_path = ensure_output_path(args.output)
    output_path.write_text(json.dumps(results, indent=2))

    print(json.dumps(results, indent=2))  # noqa: T201
    print(f"Profile results written to {output_path}")  # noqa: T201


if __name__ == "__main__":
    main()
