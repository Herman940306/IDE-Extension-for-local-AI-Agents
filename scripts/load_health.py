import asyncio
import time

import httpx

URL = "http://127.0.0.1:8001/health"
CONCURRENCY = 4
DURATION = 30.0  # seconds


async def worker(latencies: list[float], stop_at: float):
    async with httpx.AsyncClient(timeout=5.0) as client:
        while time.perf_counter() < stop_at:
            start = time.perf_counter()
            try:
                r = await client.get(URL)
                r.raise_for_status()
            except Exception:
                # record as 5s timeout-equivalent to reflect failure cost
                latencies.append(5.0)
            else:
                latencies.append(time.perf_counter() - start)


async def main():
    stop_at = time.perf_counter() + DURATION
    latencies: list[float] = []
    tasks = [
        asyncio.create_task(worker(latencies, stop_at)) for _ in range(CONCURRENCY)
    ]
    await asyncio.gather(*tasks)

    if not latencies:
        print("No results collected.")
        return

    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    p50 = latencies_sorted[int(0.50 * n) - 1]
    p90 = latencies_sorted[int(0.90 * n) - 1]
    p99 = latencies_sorted[max(int(0.99 * n) - 1, 0)]
    rps = n / DURATION

    print(f"Requests: {n}")
    print(f"RPS: {rps:.1f}")
    print(f"p50: {p50:.3f}s, p90: {p90:.3f}s, p99: {p99:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
