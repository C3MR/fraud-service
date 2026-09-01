# Benchmarks — `/v1/predict`

Load-test results for the fraud-scoring prediction endpoint.

## Method

`hey` is not available on this machine, so the numbers below come from
`bench.py` — a small async load generator (`httpx` + `asyncio`) checked into
this repo. It fires a fixed number of requests with a fixed number in flight
and measures real per-request wall-clock latency. Reproduce with:

```bash
# server (one terminal)
fastapi dev src/fraud_service/api/app.py

# load (another terminal)
python bench.py 2000 50      # 2000 requests, 50 concurrent
```

Equivalent `hey` invocation, once installed:

```bash
hey -n 2000 -c 50 -m POST -H "content-type: application/json" \
    -D payloads/sample.json http://localhost:8000/v1/predict
```

## Environment

| Item        | Value                                             |
| ----------- | ------------------------------------------------- |
| Server      | `fastapi dev` (Uvicorn, single worker, reload on) |
| Endpoint    | `POST /v1/predict`                                 |
| Payload     | `payloads/sample.json`                             |
| Requests    | 2000                                              |
| Concurrency | 50                                                |
| Platform    | Windows, Python 3.14                              |

## Results

| Metric         |     Value |
| -------------- | --------: |
| Requests/sec   |     103.4 |
| Total time     |   19.35 s |
| Latency min    |   61.6 ms |
| Latency **p50** |  360.6 ms |
| Latency p90    |  914.5 ms |
| Latency **p99** | 2478.0 ms |
| Latency max    | 5264.8 ms |
| Latency mean   |  479.1 ms |
| Non-2xx        |         0 |

## Reading the numbers

The p50→p99 spread (361 ms → 2478 ms) is the signal, not noise. `/v1/predict`
is a **synchronous** `def` route on purpose: the sklearn inference call is
CPU-bound, so FastAPI runs it in the default `anyio` worker thread pool
(~40 threads) instead of blocking the event loop. At concurrency 50 that pool
saturates, so requests past the pool size queue — which is exactly what the
long tail shows. Every request still returned 200; nothing failed, work was
simply serialised behind the available threads.

This is the correct trade-off for a single-process dev server: a synchronous
route protects the event loop from the CPU-bound call, at the cost of a tail
under high concurrency.

## Caveats

- `fastapi dev` runs a single Uvicorn worker with auto-reload enabled and is
  **not** a production configuration — absolute throughput here understates a
  real deployment.
- Production numbers should be taken from `fastapi run` (or Uvicorn/Gunicorn
  with multiple workers) inside the container, ideally the one built by
  `make image`, sized to the host's CPU count.
