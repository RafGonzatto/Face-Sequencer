"""model_manager.py - Centralized model lifecycle management (WP003)

This module provides a singleton `ModelManager` responsible for:
  * Lazy model loading (on first access)
  * Caching with LRU eviction based on a configurable memory budget
  * Explicit preload / release APIs
  * Basic memory accounting (rough estimates for torch models)
  * Introspection endpoints (stats, list models)

The intent is to decouple individual feature modules (e.g. audio alignment)
from ad‑hoc global dictionaries of models so we get: predictable memory use,
consistent logging, and the ability to warm models at application start.

Environment variables:
  FACE_SEQ_MODEL_MAX_MEMORY_MB (int)  - Soft cap for total cached model memory (default 1536 MB)
  FACE_SEQ_MODEL_EVICT_TARGET_PCT (int) - After exceeding budget, target % of budget to reach (default 85)

Public usage pattern:
  from model_manager import get_model_manager
  mm = get_model_manager()
  mm.register_model('whisperx_transcribe_tiny', loader_callable, size_estimate=120_000_000)
  model = mm.get_or_load('whisperx_transcribe_tiny')

Thread safety: All public mutating operations take an internal re‑entrant lock.
Memory estimation: For torch.nn.Module we sum parameter + buffer sizes; otherwise
`sys.getsizeof` as a fallback (coarse). Size is stored once at load time.

NOTE: We purposefully keep hard dependencies minimal; heavy imports (torch,
whisperx, etc.) happen inside loader callables supplied by feature code so that
just importing this module is cheap.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Callable, Dict, Optional, Any, List
import os
import sys
import threading

__all__ = [
    'ModelManager', 'get_model_manager', 'ModelLoadError',
]


class ModelLoadError(RuntimeError):
    """Raised when a model cannot be loaded."""
    pass


@dataclass
class _ModelEntry:
    name: str
    loader: Callable[[], Any]
    size_estimate: Optional[int] = None  # bytes
    tags: List[str] = field(default_factory=list)
    obj: Any = None
    loaded: bool = False
    load_error: Optional[str] = None
    last_access: float = field(default_factory=time)
    load_time_s: Optional[float] = None

    def touch(self):
        self.last_access = time()


class ModelManager:
    """Singleton manager for ML model lifecycle."""

    def __init__(self):  # pragma: no cover - trivial
        self._models: Dict[str, _ModelEntry] = {}
        self._lock = threading.RLock()
        self.max_memory_bytes = int(os.environ.get('FACE_SEQ_MODEL_MAX_MEMORY_MB', '1536')) * 1024 * 1024
        self.evict_target_pct = int(os.environ.get('FACE_SEQ_MODEL_EVICT_TARGET_PCT', '85'))

    # ---- Registration / Loading -------------------------------------------------
    def register_model(self, name: str, loader: Callable[[], Any], *, size_estimate: Optional[int] = None, tags: Optional[List[str]] = None) -> None:
        """Register a model loader.
        If model already registered we update metadata but keep existing object unless force reload via release()."""
        with self._lock:
            entry = self._models.get(name)
            if entry is None:
                self._models[name] = _ModelEntry(name=name, loader=loader, size_estimate=size_estimate, tags=list(tags or []))
            else:
                entry.loader = loader
                if size_estimate is not None:
                    entry.size_estimate = size_estimate
                if tags:
                    entry.tags = list(tags)

    def has_model(self, name: str) -> bool:
        with self._lock:
            e = self._models.get(name)
            return bool(e and e.loaded and e.obj is not None)

    def get(self, name: str) -> Any:
        with self._lock:
            entry = self._models.get(name)
            if not entry or not entry.loaded or entry.obj is None:
                raise KeyError(f"Model '{name}' not loaded")
            entry.touch()
            return entry.obj

    def get_or_load(self, name: str) -> Any:
        with self._lock:
            entry = self._models.get(name)
            if entry is None:
                raise KeyError(f"Unknown model '{name}' (not registered)")
            if not entry.loaded:
                self._load_entry(entry)
            entry.touch()
            return entry.obj

    def preload(self, names: List[str]) -> Dict[str, str]:
        """Attempt to load multiple models; returns status mapping."""
        result = {}
        for n in names:
            try:
                if self.has_model(n):
                    result[n] = 'already_loaded'
                else:
                    self.get_or_load(n)
                    result[n] = 'loaded'
            except Exception as e:  # noqa: BLE001
                result[n] = f'error: {e}'
        return result

    def release(self, name: str) -> bool:
        with self._lock:
            entry = self._models.get(name)
            if not entry or not entry.loaded:
                return False
            # Try to free GPU memory proactively
            try:  # pragma: no cover - environment dependent
                import torch  # type: ignore
                if isinstance(entry.obj, torch.nn.Module):
                    del entry.obj
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                else:
                    entry.obj = None
            except Exception:  # torch not installed or other cleanup issue
                entry.obj = None
            entry.loaded = False
            return True

    # ---- Internal helpers -------------------------------------------------------
    def _load_entry(self, entry: _ModelEntry) -> None:
        t0 = time()
        try:
            obj = entry.loader()
            entry.obj = obj
            entry.loaded = True
            entry.load_time_s = time() - t0
            if entry.size_estimate is None:
                entry.size_estimate = self._estimate_size(obj)
            # Enforce memory limits after successful load
            self._enforce_limits()
        except Exception as e:  # noqa: BLE001
            entry.load_error = str(e)
            raise ModelLoadError(f"Failed to load model '{entry.name}': {e}") from e

    def _estimate_size(self, obj: Any) -> int:
        # Torch model size calculation (parameters + buffers)
        try:  # pragma: no cover - depends on torch install
            import torch  # type: ignore
            if isinstance(obj, torch.nn.Module):
                total = 0
                for p in obj.parameters():
                    total += p.numel() * p.element_size()
                for b in obj.buffers():
                    total += b.numel() * b.element_size()
                return total
        except Exception:  # torch not available
            pass
        # Fallback coarse estimate
        try:
            return sys.getsizeof(obj)
        except Exception:
            return 0

    # ---- Memory / Eviction ------------------------------------------------------
    def total_memory_bytes(self) -> int:
        with self._lock:
            return sum((e.size_estimate or 0) for e in self._models.values() if e.loaded)

    def _enforce_limits(self) -> None:
        with self._lock:
            total = self.total_memory_bytes()
            if total <= self.max_memory_bytes:
                return
            target = int(self.max_memory_bytes * (self.evict_target_pct / 100.0))
            # Evict least recently accessed loaded models until under target
            loaded_entries = [e for e in self._models.values() if e.loaded]
            loaded_entries.sort(key=lambda e: e.last_access)  # oldest first
            freed = 0
            for e in loaded_entries:
                if total - freed <= target:
                    break
                freed += (e.size_estimate or 0)
                self.release(e.name)

    # ---- Introspection ----------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'max_memory_bytes': self.max_memory_bytes,
                'current_memory_bytes': self.total_memory_bytes(),
                'registered_models': len(self._models),
                'loaded_models': sum(1 for e in self._models.values() if e.loaded),
                'models': [
                    {
                        'name': e.name,
                        'loaded': e.loaded,
                        'size_bytes': e.size_estimate,
                        'tags': e.tags,
                        'load_time_s': e.load_time_s,
                        'last_access': e.last_access,
                        'error': e.load_error,
                    } for e in self._models.values()
                ]
            }


# ---- Singleton access -----------------------------------------------------------
_global_manager: Optional[ModelManager] = None
_global_lock = threading.Lock()

def get_model_manager() -> ModelManager:
    global _global_manager
    with _global_lock:
        if _global_manager is None:
            _global_manager = ModelManager()
        return _global_manager
