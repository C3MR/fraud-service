"""Tiny async load generator - a hey substitute for environments without it.

Fires N requests at CONCURRENCY in flight against /v1/predict and reports
p50/p90/p99 latency, requests/sec, and the status-code breakdown. Numbers
are real (measured wall-clock per request), not estimates.

Usage:
    python bench.py                 # defaults: 2000 requests, 50 concurrent
    python bench.py 5000 100        # 5000 requests, 100 concurrent
"""
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

URL = "http://localhost:8000/v1/predict"
PAYLOAD = json.loads(Path("payloads/sample.json").read_text(encoding="utf-8"))


def percentile(values, pct):
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


async def worker(client, queue, latencies, statuses):
    while True:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        t0 = time.perf_counter()
        try:
            r = await client.post(URL, json=PAYLOAD)
            statuses[r.status_code] += 1
        except Exception as exc:
            statuses[f"error:{type(exc).__name__}"] += 1
        finally:
            latencies.append((time.perf_counter() - t0) * 1000)
        queue.task_done()


async def main(total, concurrency):
    queue = asyncio.Queue()
    for _ in range(total):
        queue.put_nowait(1)

    latencies = []
    statuses = Counter()

    limits = httpx.Limits(max_connections=concurrency,
                          max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        wall0 = time.perf_counter()
        workers = [asyncio.create_task(
            worker(client, queue, latencies, statuses))
            for _ in range(concurrency)]
        await asyncio.gather(*workers)
        wall = time.perf_counter() - wall0

    rps = total / wall if wall else 0.0
    print()
    print(f"  Target        : {URL}")
    print(f"  Requests      : {total}   Concurrency: {concurrency}")
    print(f"  Total time    : {wall:.2f} s")
    print(f"  Requests/sec  : {rps:.1f}")
    print()
    print("  Latency (ms):")
    print(f"    min   : {min(latencies):.1f}")
    print(f"    p50   : {percentile(latencies, 50):.1f}")
    print(f"    p90   : {percentile(latencies, 90):.1f}")
    print(f"    p99   : {percentile(latencies, 99):.1f}")
    print(f"    max   : {max(latencies):.1f}")
    print(f"    mean  : {sum(latencies) / len(latencies):.1f}")
    print()
    print(f"  Status codes  : {dict(statuses)}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    c = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    asyncio.run(main(n, c))
