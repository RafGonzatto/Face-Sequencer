"""Lightweight performance smoke tests.

Disabled by default; enable with PERF=1 environment variable.
Measures average latency over multiple rapid calls to inexpensive endpoints.
"""
from __future__ import annotations

import os
import time
import statistics as stats

import pytest
from app import app

RUNS = 20


@pytest.mark.skipif(os.getenv('PERF') != '1', reason='Set PERF=1 to enable performance smoke tests')
def test_status_endpoint_latency():
    app.config.update(TESTING=True)
    latencies = []
    with app.test_client() as c:
        # Warmup
        c.get('/api/audio/status')
        for _ in range(RUNS):
            t0 = time.perf_counter()
            r = c.get('/api/audio/status')
            assert r.status_code == 200
            latencies.append((time.perf_counter() - t0) * 1000)
    mean = stats.mean(latencies)
    p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1]
    # Loose guard rails: ensure mean under 50ms in test environment
    assert mean < 50, f"Mean latency too high: {mean:.2f}ms"
    # p95 under 80ms
    assert p95 < 80, f"p95 latency too high: {p95:.2f}ms"
