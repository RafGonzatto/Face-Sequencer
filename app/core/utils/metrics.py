"""metrics.py - Lightweight in-process metrics collection (WP006)

Collects timing statistics and request metadata without external deps.
Thread-safe and zero-config; suitable for development and lightweight prod.
"""
from __future__ import annotations

import time
import threading
from contextlib import contextmanager
from typing import Dict, Any

_lock = threading.Lock()
_start_time = time.perf_counter()

_timers: Dict[str, Dict[str, float]] = {}
_requests: Dict[str, float] = {
    'count': 0,
    'total_ms': 0.0,
    'last_ms': 0.0,
}


def record_timing(name: str, duration_ms: float) -> None:
    """Record a timing sample in milliseconds."""
    with _lock:
        bucket = _timers.setdefault(name, {'count': 0, 'total_ms': 0.0, 'last_ms': 0.0})
        bucket['count'] += 1
        bucket['total_ms'] += float(duration_ms)
        bucket['last_ms'] = float(duration_ms)


@contextmanager
def time_block(name: str):
    """Context manager to time a code block."""
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        record_timing(name, (end - start) * 1000.0)


def record_request(duration_ms: float):
    with _lock:
        _requests['count'] += 1
        _requests['total_ms'] += float(duration_ms)
        _requests['last_ms'] = float(duration_ms)


def uptime_seconds() -> float:
    return time.perf_counter() - _start_time


def snapshot() -> Dict[str, Any]:
    with _lock:
        timers_copy = {k: v.copy() for k, v in _timers.items()}
        # Derive averages
        for k, v in timers_copy.items():
            if v['count']:
                v['avg_ms'] = v['total_ms'] / v['count']
        req_copy = _requests.copy()
        if req_copy['count']:
            req_copy['avg_ms'] = req_copy['total_ms'] / req_copy['count']
    return {
        'uptime_seconds': uptime_seconds(),
        'timers': timers_copy,
        'requests': req_copy,
    }


def reset():  # pragma: no cover - utility for future tests
    with _lock:
        _timers.clear()
        _requests.update({'count': 0, 'total_ms': 0.0, 'last_ms': 0.0})