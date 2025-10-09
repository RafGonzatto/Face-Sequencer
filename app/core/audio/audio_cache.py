"""audio_cache.py - Shared audio processing cache utilities (WP002)

Enhanced in WP002 to support:
 - TTL expiration (already existed) + explicit per-call override
 - LRU size limiting
 - File change invalidation via (hash + mtime) in cache key
 - Hit / miss / eviction metrics
 - Observable statistics endpoint (/api/cache/stats)
"""
from __future__ import annotations

import json
import os
import hashlib
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class AudioCacheEntry:
    """Container for cached audio processing results."""
    value: Any
    file_hash: str
    params_signature: str
    created_at: float

    def is_expired(self, ttl_seconds: Optional[float]) -> bool:
        if ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > ttl_seconds


class AudioCache:
    """Thread-safe LRU cache keyed by audio content hash and parameters.

    Key format (namespace:file_hash:file_mtime:params_signature)
    - file_hash ensures identical content reuse
    - file_mtime ensures automatic invalidation when file changes without content hash change (rare but defensive)
    - params_signature differentiates processing parameter variants
    """

    def __init__(self, max_entries: int = 128, ttl_seconds: Optional[float] = 900):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._store: "OrderedDict[str, AudioCacheEntry]" = OrderedDict()
        self._lock = threading.Lock()
        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._sets = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                self._misses += 1
                return None
            if entry.is_expired(self.ttl_seconds):
                self._store.pop(key, None)
                self._misses += 1
                return None
            # Maintain LRU ordering
            self._store.move_to_end(key)
            self._hits += 1
            return deepcopy(entry.value)

    def set(self, key: str, value: Any, file_hash: str, params_signature: str) -> None:
        with self._lock:
            self._store[key] = AudioCacheEntry(
                value=deepcopy(value),
                file_hash=file_hash,
                params_signature=params_signature,
                created_at=time.time(),
            )
            self._store.move_to_end(key)
            self._sets += 1
            self._enforce_capacity()

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def invalidate_by_file_hash(self, file_hash: str) -> None:
        with self._lock:
            keys_to_remove = [k for k, entry in self._store.items() if entry.file_hash == file_hash]
            for key in keys_to_remove:
                self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def _enforce_capacity(self) -> None:
        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)
            self._evictions += 1

    # ---------------------------
    # Stats / Metrics
    # ---------------------------
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            size_bytes = 0
            # Approximate size via JSON serialization fallback; keep lightweight
            for entry in self._store.values():
                try:
                    size_bytes += len(json.dumps(entry.value, default=str))
                except Exception:
                    # If non-serializable, skip precise sizing
                    pass
            total = self._hits + self._misses if (self._hits + self._misses) > 0 else 1
            return {
                'entries': len(self._store),
                'max_entries': self.max_entries,
                'ttl_seconds': self.ttl_seconds,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(self._hits / total, 4),
                'evictions': self._evictions,
                'sets': self._sets,
                'approx_value_bytes': size_bytes,
            }

    def as_serializable(self) -> Dict[str, Any]:
        data = self.stats()
        return data


def _hash_from_params(params: Optional[Dict[str, Any]]) -> str:
    if not params:
        return "noop"
    try:
        serialized = json.dumps(params, sort_keys=True, default=str)
    except TypeError:
        # Fallback to repr for non-serializable objects
        serialized = repr(params)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def hash_audio_file(file_path: str, chunk_size: int = 1 << 16) -> str:
    """Compute SHA256 hash of an audio file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    sha = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def _file_mtime(file_path: str) -> int:
    try:
        return int(os.path.getmtime(file_path))
    except OSError:
        return 0


def generate_cache_key(file_path: str, params: Optional[Dict[str, Any]] = None, *, namespace: str = "default") -> Tuple[str, str, str]:
    """Create deterministic cache key using file hash + mtime and parameter signature.

    Returns (key, file_hash, params_signature)
    """
    file_hash = hash_audio_file(file_path)
    file_mtime = _file_mtime(file_path)
    params_signature = _hash_from_params(params)
    return f"{namespace}:{file_hash}:{file_mtime}:{params_signature}", file_hash, params_signature


# Shared cache instance used across the application
_audio_cache = AudioCache()


def get_audio_cache() -> AudioCache:
    return _audio_cache


# Convenience shorthand used by callers
audio_cache = get_audio_cache()


__all__ = [
    "AudioCache",
    "AudioCacheEntry",
    "audio_cache",
    "generate_cache_key",
    "get_audio_cache",
    "hash_audio_file",
]
